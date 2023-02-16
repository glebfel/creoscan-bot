import logging
from dataclasses import dataclass

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
)

from addons.Trottling import handle_trottling_decorator
from common.decorators import (
    handle_common_exceptions_decorator,
    inform_user_decorator,
)
from models import BotModule
from ..base import callback as base_callback
from ..base import get_modules_buttons

log = logging.getLogger(__name__)


@dataclass
class IntroductionModule(BotModule):
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


module = IntroductionModule(name='introduction')


@Client.on_message(filters.command('start'))
@handle_common_exceptions_decorator
@handle_trottling_decorator
@inform_user_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)

