from pyrogram.types import (
    Message,
)

import exceptions
from helpers.base import BaseHelper, api_adapter_module


class WithHelperDecorator:
    """
    Decorator tries to obtain search results from a given Helper and pass
    them to the decorated function.
    If Helper rises an exception, the given message is used to reply to.
    """
    def __init__(self, helper_class: BaseHelper, error_text: str = ''):
        self._helper_class = helper_class
        self._error_text = error_text or api_adapter_module.unhandled_error_text

    def __call__(self, func):
        async def wrapped_func(*args, **kwargs):
            if any(isinstance(message := arg, Message) for arg in args):
                try:
                    await func(helper_data=await self._helper_class(message).search_results, *args, **kwargs)
                except exceptions.AccountIsPrivate:
                    await message.reply(text=api_adapter_module.error_text_account_private, reply_to_message_id=message.id)
                except exceptions.AccountNotExist:
                    await message.reply(text=api_adapter_module.error_text_account_not_found, reply_to_message_id=message.id)
                except exceptions.EmptyResultsException:
                    await message.reply(text=self._error_text, reply_to_message_id=message.id)  # TODO fix
                except exceptions.ThirdPartyApiException:
                    await message.reply(api_adapter_module.unhandled_error_text)
                    raise  # unhanled error, let top-level decorator to know about it
                except exceptions.WrongInputException:
                    await message.reply(text=api_adapter_module.wrong_input_text, reply_to_message_id=message.id)

        return wrapped_func
