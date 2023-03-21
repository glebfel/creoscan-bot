import datetime
from dataclasses import dataclass, field

import validators
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
from common.models import ThirdPartyAPISource
from exceptions import WrongInputException
from helpers.state import redis_connector
from jobs import scheduler, start_monitoring
from models import BotModule
from plugins.base import callback as base_callback, get_modules_buttons


@dataclass
class MonitoringModule(BotModule):
    instagram_media_type_choice_text: str = field(init=False)
    subscribe_confirmation_text: str = field(init=False)
    subscribe_text: str = field(init=False)

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


@Client.on_message(filters.regex(rf'^{module.button}$') |
                   filters.command(module.command) | filters.regex(module.return_button))
@inform_user_decorator
@handle_trottling_decorator
@handle_common_exceptions_decorator
@handle_paid_requests_trottling_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)


@Client.on_callback_query(filters.regex('^SUBSCRIBE'))
@handle_common_exceptions_decorator
async def handle_subscribe(client: Client, callback_query: CallbackQuery) -> None:
    # extract user data from redis
    social_network = await redis_connector.get_user_data(key='social_network',
                                                         user_id=callback_query.from_user.id)
    nickname = await redis_connector.get_user_data(key='nickname',
                                                   user_id=callback_query.from_user.id)
    media_type = await redis_connector.get_user_data(key='selected_media_type',
                                                     user_id=callback_query.from_user.id)

    start_time = datetime.datetime.now()
    if current_jobs := scheduler.get_jobs():
        channel_stats_jobs = list(filter(lambda j: j.id.startswith('tiktok-media'), current_jobs))
        if channel_stats_jobs:
            last_job = channel_stats_jobs[-1]
            start_time = last_job.next_run_time

    start_time += datetime.timedelta(seconds=settings.PENDING_DELAY)

    scheduler.add_job(
        start_monitoring,
        id=f'monitoring-{social_network}-{nickname}',
        trigger='date',
        name=f'Monitoring for {nickname}',
        misfire_grace_time=None,  # run job even if it's time is overdue
        kwargs={
            'client': client,
            'module': module,
            'message': callback_query.message,
            'social_network': social_network,
            'nickname': nickname,
            'media_type': media_type
        },
        run_date=start_time,
    )

    text = module.subscribe_text.format(
        social_network=social_network.capitalize(),
        nickname=nickname, )

    await callback_query.message.reply_text(text=text)


@Client.on_callback_query(filters.regex('^CONFIRM_SUBSCRIBE'))
@handle_common_exceptions_decorator
async def handle_subscribe_confirmation(client: Client, callback_query: CallbackQuery) -> None:
    # extract user data from redis
    user_selected_media_type = await redis_connector.get_user_data(key='selected_media_type',
                                                                   user_id=callback_query.from_user.id)
    social_network = await redis_connector.get_user_data(key='social_network',
                                                         user_id=callback_query.from_user.id)
    nickname = await redis_connector.get_user_data(key='nickname',
                                                   user_id=callback_query.from_user.id)

    text = module.subscribe_confirmation_text.format(
        social_network=social_network.capitalize(),
        nickname=nickname,
        media_list=f'◾ {user_selected_media_type}\n')

    await callback_query.message.reply_text(text=text,
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(module.subscribe_button,
                                                                       callback_data='SUBSCRIBE')]]))


@Client.on_callback_query(filters.regex('^SELECT'))
@handle_common_exceptions_decorator
async def choose_media_type(client: Client, callback_query: CallbackQuery) -> None:
    """
    Handles include/exclude button. Redraws original message with the
    same, and changes entity (e.g. emoji) that represents selected hashtag.
    """
    # stashed hashtags contains only selected by user
    media_types_selected: str = callback_query.data.replace('SELECT', '')

    # save media type to redis storage
    await redis_connector.save_user_data(
        key='selected_media_type',
        data=media_types_selected,
        user_id=callback_query.from_user.id,
    )

    await callback_query.message.edit_reply_markup(
        get_keyboard_select_media_type(
            selected=media_types_selected,
            social_network=ThirdPartyAPISource.instagram
        ))


def get_keyboard_select_media_type(social_network: ThirdPartyAPISource, selected: str = None) -> InlineKeyboardMarkup:
    if social_network == ThirdPartyAPISource.instagram:
        media_type_buttons = [
            [
                InlineKeyboardButton(
                    media_type,  # actually max for Tg button is 64
                    callback_data='PASS',  # button press will do nothing
                ),
                InlineKeyboardButton(
                    module.button_selected if str(
                        media_type
                    ) == selected else module.button_unselected,
                    callback_data=f'SELECT{str(media_type)}',
                ),
            ] for media_type in (module.stories_button, module.posts_button, module.reels_button)
        ]
        markup = [
            *media_type_buttons,
            [InlineKeyboardButton(module.subscribe_button, callback_data='CONFIRM_SUBSCRIBE')],
        ]
    else:
        markup = [
            [InlineKeyboardButton(module.subscribe_button, callback_data='SUBSCRIBE')],
        ]
    return InlineKeyboardMarkup(markup)


@Client.on_message(filters.text & conversation_filter(module.name))
@handle_trottling_decorator
@handle_common_exceptions_decorator
@inform_user_decorator
async def handle_user_link_input(client: Client, message: Message) -> None:
    nickname = extract_username_from_link(message)

    await redis_connector.save_user_data(
        key='nickname',
        data=nickname,
        user_id=message.from_user.id)

    if 'tiktok' in message.text.lower():
        await redis_connector.save_user_data(
            key='social_network',
            data=ThirdPartyAPISource.tiktok.value,
            user_id=message.from_user.id,
        )

        await message.reply_text(
            text=module.subscribe_confirmation_text.format(nickname=nickname,
                                                           social_network=ThirdPartyAPISource.tiktok.value.capitalize(),
                                                           media_list=f'◾ Видео'),
            reply_markup=get_keyboard_select_media_type(social_network=ThirdPartyAPISource.tiktok))

    else:
        await redis_connector.save_user_data(
            key='social_network',
            data=ThirdPartyAPISource.instagram.value,
            user_id=message.from_user.id,
        )

        await message.reply_text(
            text=module.instagram_media_type_choice_text.format(nickname=nickname),
            reply_markup=get_keyboard_select_media_type(social_network=ThirdPartyAPISource.instagram))


def extract_username_from_link(message: Message) -> str:
    if not (link := message.text) or not validators.url(message.text):
        raise WrongInputException(message.text or message.media)
    return '@' + link.strip('/').split('/')[-1].replace('@', '')
