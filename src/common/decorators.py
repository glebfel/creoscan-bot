import logging

from pyrogram.enums import ChatAction
from pyrogram.types import CallbackQuery, Message

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
