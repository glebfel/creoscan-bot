from dataclasses import dataclass, field

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from addons.Telemetry import SendUserActionEventDecorator
from addons.Trottling import (
    handle_paid_requests_trottling_decorator,
    handle_trottling_decorator,
)
from common.decorators import (
    handle_common_exceptions_decorator,
    inform_user_decorator,
)
from models import BotModule
from plugins.base import callback as base_callback


@dataclass
class SupportModule(BotModule):
    button_contact: str = field(init=False)
    url_contact: str = field(init=False)

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(self.button_contact, url=self.url_contact)]
        ])


module = SupportModule('support')


@Client.on_message(filters.regex(rf'^{module.button}$') | filters.command(module.command))
@handle_common_exceptions_decorator
@handle_trottling_decorator
@SendUserActionEventDecorator(in_module=module.name)
@inform_user_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)
