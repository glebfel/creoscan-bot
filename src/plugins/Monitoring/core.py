import datetime
from dataclasses import dataclass, field

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)

import settings
from addons.Trottling import handle_trottling_decorator, handle_paid_requests_trottling_decorator
from common.decorators import (
    inform_user_decorator, handle_common_exceptions_decorator,
)
from common.filters import conversation_filter
from helpers.state import redis_connector
from helpers.utils import get_helper_class_from_link_tiktok
from jobs import scheduler, get_tiktok_media
from models import BotModule
from plugins.base import callback as base_callback, get_modules_buttons


@dataclass
class MonitoringModule(BotModule):
    tiktok_link_input_text: str = field(init=False)
    instagram_link_input_text: str = field(init=False)

    return_button: str = field(init=False)
    my_monitoring_button: str = field(init=False)
    button_selected: str = field(init=False)
    button_unselected: str = field(init=False)
    subscribe_button: str = field(init=False)
    stories_button: str = field(init=False)
    posts_button: str = field(init=False)
    reels_button: str = field(init=False)

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        support_button = get_modules_buttons()[-1]
        buttons = [self.my_monitoring_button, support_button, self.return_button, ]
        extra_buttons = []

        # align buttons in two columns
        bottom_menu_keys_iterator = iter(buttons)

        buttons_in_columns = list(
            zip(bottom_menu_keys_iterator, bottom_menu_keys_iterator)
        )

        # if number of buttons is odd, add missing one
        if len(buttons) % 2 != 0:
            extra_buttons.append(buttons[-1])

        """
        Buttons for ReplyKeyboardMarkup shoul be in form of:
        [ (button1, button2), (button3, button4), ... ]
        """
        buttons_in_columns.append(extra_buttons)

        return ReplyKeyboardMarkup(
            list(buttons_in_columns),
            one_time_keyboard=False,
            placeholder=self.friendly_name,
            resize_keyboard=True,
        )


module = MonitoringModule('monitoring')


@Client.on_message(filters.regex(rf'^{module.button}$') | filters.command(module.command) | filters.regex(module.return_button))
@inform_user_decorator
@handle_trottling_decorator
@handle_common_exceptions_decorator
@handle_paid_requests_trottling_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)


@Client.on_callback_query(filters.regex('^SELECT'))
@handle_common_exceptions_decorator
async def choose_media_type(client: Client, callback_query: CallbackQuery) -> None:
    """
    Handles include/exclude button. Redraws original message with the
    same, and changes entity (e.g. emoji) that represents selected hashtag.
    """
    # stashed hashtags contains only selected by user
    media_types_selected = []
    changed_media_type: str = callback_query.data.replace('SELECT', '')

    try:
        media_types_selected.remove(changed_media_type)
    except ValueError:
        media_types_selected.append(changed_media_type)

    # save media type to redis storage
    await _save_media_type(
        media_type=media_types_selected,
        user_id=callback_query.from_user.id,
    )

    await callback_query.message.edit_reply_markup(
        get_keyboard_select_media_type(
            selected=media_types_selected,
        ))


@Client.on_callback_query(filters.regex(module.subscribe_button))
@handle_common_exceptions_decorator
async def choose_media_type(client: Client, callback_query: CallbackQuery) -> None:
    pass


def get_keyboard_select_media_type(selected: list = None) -> InlineKeyboardMarkup:
    selected = selected if selected else []
    media_type_buttons: list = [
        [
            InlineKeyboardButton(
                media_type,  # actually max for Tg button is 64
                callback_data='PASS',  # button press will do nothing
            ),
            InlineKeyboardButton(
                module.button_selected if str(
                    media_type
                ) in selected else module.button_unselected,
                callback_data=f'SELECT{str(media_type)}',
            ),
        ] for media_type in (module.stories_button, module.posts_button, module.reels_button)
    ]

    return InlineKeyboardMarkup([
        *media_type_buttons,
        [InlineKeyboardButton(module.subscribe_button)],
    ])


@Client.on_message(filters.text & conversation_filter(module.name))
@handle_trottling_decorator
@handle_common_exceptions_decorator
@inform_user_decorator
async def handle_user_link_input(client: Client, message: Message) -> None:
    if 'tiktok' in message.text.lower():
        await message.reply_text(
            text=module.tiktok_link_input_text,
            reply_markup=get_keyboard_select_media_type(),
        )
    else:
        await message.reply_text(
            text=module.instagram_link_input_text,
            reply_markup=get_keyboard_select_media_type())


# for saving media type to redis storage
async def _get_media_type(user_id: int) -> list[str]:
    media_type_from_storage: list = await redis_connector.get_user_data(
        key=user_id,
        user_id=user_id,
    ) or await redis_connector.get_user_data(  # deprecated: fallback
        key='hashtags_cloud',
        user_id=user_id,
    ) or []
    return media_type_from_storage


async def _save_media_type(media_type: list, user_id: int) -> None:
    await redis_connector.save_user_data(
        key=user_id,
        data=media_type,
        user_id=user_id,
    )


async def _delete_media_type(user_id: int) -> None:
    await redis_connector.delete_user_data(
        key=user_id,
        user_id=user_id,
    )
