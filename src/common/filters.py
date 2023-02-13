import logging
from pyrogram import filters
from pyrogram.types import Message

from helpers.state import redis_connector
from plugins.base import get_modules_buttons, get_modules_commands


log = logging.getLogger(__name__)


def conversation_filter(allowed_in_conversation: str):
    async def filter_by_conversation(filter_, client, update) -> bool:

        # message can be sent on behalf of group chat
        if not update.from_user:
            return False

        if hasattr(update, 'text'):
            if update.text in get_modules_buttons():
                return False

            if update.text in get_modules_commands():
                return False

        sender = update.from_user.id

        """
        `allowed_in_conversation` is passed by a module and defines if sent command/message is
        allowed in this conversation.
        `current_conversation` is retrieved from saved user state. It can be None if user is in Introduction state.

        if user is in appropriate conversation (i.e. has a saved state) - continue handling user's message
        if not - pass message to next handler.
        """
        current_conversation: str = await redis_connector.get_user_data(
            key='conversation',
            user_id=sender,
        ) or None

        return filter_.allowed_in_conversation == current_conversation

    return filters.create(
        filter_by_conversation,
        'ConversationFilter',
        allowed_in_conversation=allowed_in_conversation,
    )
