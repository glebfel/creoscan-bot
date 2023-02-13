import logging
from dataclasses import dataclass, field
from typing import Any, List

from pyrogram.types import Message

from exceptions import (
    AccountIsPrivate,
    AccountNotExist,
    EmptyResultsException,
    ThirdPartyApiException,
)
from models import Module

from .clients import (
    BaseThirdPartyAPIClient,
    RapidAPIClient,
)


@dataclass
class APIAdapterModule(Module):
    error_text_account_not_found: str = field(init=False)
    error_text_account_private: str = field(init=False)
    error_text_first_provider_failed: str = field(init=False)


api_adapter_module = APIAdapterModule('api_adapter')
log = logging.getLogger(__name__)


class BaseHelper:
    """
    Helper has a list of clients.
    If helper has a method, the method will be executed.
    If method fails the next helper with same method will be picked up.

    Adapter has some integration with Telegram Bot Module in form of replying
    to initial message in case of error.
    Also initial messsage is used to obtain a keyword for the search method.
    Exact way of extracting keyword should be provided in subclass.
    """
    _search_results = None  # cache for obtained search results

    clients = (
        RapidAPIClient,
    )

    def __init__(self, message: Message):
        # load external configs
        super().__init__()

        # save message for a future use (e.g. replies to user)
        # message is also used to extract a keyword, implementation of extraction
        # supposed to be implemented in subclass
        self._message = message

    @property
    def keyword(self):
        # keyword should be extracted from self._message.
        # Implement in subclass.
        raise NotImplementedError

    @property
    def suitable_clients(self):
        log.debug(
            'Suitable clients for `%s` are: %s',
            self._search_method,
            clients := [c for c in self.clients if hasattr(c, self._search_method)],
        )
        return clients

    @property
    async def search_results(self) -> List[Any]:
        # update results if there is no cache
        if not self._search_results:
            # probably iterator would be better here, but we need to know if exception is raised
            # at the beginning of loop
            for helper in self.suitable_clients:
                # TODO yield iterator, inform in addon
                self._search_results = await self._search_with_helper(helper)
                if self._search_results:
                    break  # if we obtained data, do not continue w/ other clients

        if not self._search_results:
            # all providers failed to get data
            raise EmptyResultsException(f'No results for {self.keyword}')

        return self._search_results

    async def _search_with_helper(self, client: BaseThirdPartyAPIClient) -> List[Any]:
        try:
            search_method = getattr(client(), self._search_method)

            log.debug('Trying to perform search of "%s" with %s', self.keyword, search_method)

            if not (result := await search_method(self.keyword)):
                # provider failed, but probably the next one will find something
                raise EmptyResultsException(f'{client.api_provider_name} found nothing for {self.keyword}')

            # request with provider was sucessful and not empty
            return result
        except (AccountIsPrivate, AccountNotExist):  # these errors are permanent
            raise
        except (EmptyResultsException, ThirdPartyApiException) as exc:  # these errors are retriable
            # inform user about delay
            # TODO return nothing
            await self._message.reply(
                text=api_adapter_module.error_text_first_provider_failed,
                reply_to_message_id=self._message.id,
            )

            if isinstance(exc, ThirdPartyApiException):
                log.warning('Third party exception for helper `%s`: %s', search_method, exc)
