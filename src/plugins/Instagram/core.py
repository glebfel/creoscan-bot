from dataclasses import dataclass, field

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    Message,
)

from common.decorators import (
    inform_user_decorator,
)
from models import BotModule
from plugins.base import callback as base_callback, get_modules_buttons


@dataclass
class InstagramModule(BotModule):
    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        buttons = get_modules_buttons()
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


module = InstagramModule('instagram')


@Client.on_message(filters.regex(rf'^{module.button}$') | filters.command(module.command))
# @handle_common_exceptions_decorator
@inform_user_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)