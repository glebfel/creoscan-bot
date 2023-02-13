import logging

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    Message,
)

from common.decorators import (
    handle_common_exceptions_decorator,
)
from helpers.state import redis_connector
from addons.Telemetry import (
    EventLabelCommonActionValue,
    SendUserActionEventDecorator,
)
from models import Module


common_module = Module('common')
log = logging.getLogger(__name__)


@Client.on_message(filters.text)
@handle_common_exceptions_decorator
async def help_command(client: Client, update: CallbackQuery | Message) -> str:
    """Handles all unknown commands/messages."""

    # if update is a text message from a human - reply to it
    if isinstance(update, Message) and update.from_user and not update.from_user.is_bot:
        current_conversation = await redis_connector.get_user_data(
            key='conversation',
            user_id=update.from_user.id,
        )

        current_conversation_friendly_name = getattr(
            common_module, str(current_conversation), {}
        ).get('friendly_name')

        help_text = common_module.unknown_command_text
        if current_conversation_friendly_name:
            current_module_text = common_module.current_module_text\
                .replace('{}', f'**{current_conversation_friendly_name}**')
            back_text = common_module.help_command_text
            help_text = f'{help_text}\n\n{current_module_text}\n{back_text}'
        await update.reply(text=help_text)
