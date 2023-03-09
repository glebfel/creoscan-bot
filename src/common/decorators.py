import logging

from pyrogram import Client
from pyrogram.enums import ChatAction
from pyrogram.types import CallbackQuery, Message

from common.models import UserRoleBit
from db.connector import database_connector
from utils import check_permission
from .utils import perform_func_with_error_handling

log = logging.getLogger(__name__)


def handle_common_exceptions_decorator(func):
    """
    Handles all common Telegram exceptions,
    should be used with any functions that talk to Telegram API
    """
    async def wrapper(*args, **kwargs):
        await perform_func_with_error_handling(func, *args, **kwargs)
    return wrapper


def inform_user_decorator(func):
    """
    Informs user that process is running via
      - button spinner
      - "Typing..." chat action

    and handles all common Telegram exceptions,
    should be used with any methods that talk to Telegram API
    """
    async def wrapper(*args, **kwargs):
        """
        Presence of callback_query indicates that action was triggered by UI button
        and the button has an animated spinner on it. Spinner stops rotating when
        callback_query is answered, so answering it *after* action is finished is a good way
        to indicate running process to user.
        However, if callback_query is not answered for too long, it can't be answered at all.

        When there's no callback_query (i.e. action is triggered by message or command) we
        use chat_action (which is "Typing..." indicator in chat UI header) to inform user
        that a process is running.
        However, time of this indicator can't be controlled and equals to 5 sec.
        """
        update = next(filter(lambda arg: isinstance(arg, (CallbackQuery, Message)), args), None)

        if isinstance(update, Message):
            await update.reply_chat_action(action=ChatAction.PLAYING)

        await func(*args, **kwargs)

        # answer query => stop showing animated circle on button
        if isinstance(update, CallbackQuery):
            await update.answer('Готово')

    return wrapper


def restricted_method_decorator(func):
    """
    Checks user permissions before executing the Handler method
    """
    async def wrapper(instance, client: Client, update: CallbackQuery | Message):
        from common.commands import help_command

        allowed_role: UserRoleBit = instance.allowed_role
        user_role: int = (await database_connector.get_user(user_id=update.from_user.id)).role

        log.debug(
            'Checking user "%s" role "%s" before accessing module "%s" with restriction "%s"',
            update.from_user.id,
            user_role,
            instance,
            allowed_role,
        )

        if not await check_permission(user_role, allowed_role):
            log.warning('User "%s" has no access rights for module "%s"', update.from_user.id, instance)
            # treat command as unknown if user is not allowed to use it
            return await help_command(client, update)

        return await func(instance, client, update)

    return wrapper
