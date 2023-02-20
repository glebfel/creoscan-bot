import json
import logging

import aiohttp

import settings
from exceptions import (
    AccountIsPrivate,
    AccountNotExist,
    EmptyResultsException,
    ThirdPartyApiException,
    ThirdPartyTimeoutError
)

log = logging.getLogger(__name__)


class BaseThirdPartyAPIClient:
    """
    Base class provides async request to some third-party API defined in subclass.
    Also it performs basic response codes/errors handling.
    """
    api_provider_name = ''
    auth = None
    headers = {}

    async def request(self, edge: str, url: str,
                      is_json: bool = True, proxy: str = None, querystring: dict = None) -> list:
        async with aiohttp.ClientSession(auth=self.auth, headers=self.headers) as session:
            async with session.get(
                    '/'.join((url, edge)),
                    params=querystring,
                    proxy=proxy,
            ) as res:
                return await self._clean_response(res, is_json=is_json)

    async def _clean_response(self, res, is_json: bool) -> dict:
        response_cleaned = ''

        try:
            response_cleaned = await res.content.read()

            if res.status == 404:
                raise AccountNotExist(f'{self.api_provider_name} found nothing')
            if res.status == 500:
                raise EmptyResultsException(f'{self.api_provider_name} found nothing')
            if res.status == 504:
                raise ThirdPartyTimeoutError(f'{self.api_provider_name} timeout')
            if res.status != 200:
                raise ThirdPartyApiException(
                    f'{self.api_provider_name} non-200 response. Res [{res.status}] ({res}): {response_cleaned}')
            if is_json:
                response_cleaned: dict = json.loads(response_cleaned)
                # log
                if response_cleaned:
                    log.debug('Json response: %s', response_cleaned.keys()
                        if isinstance(response_cleaned, dict) else response_cleaned[0].keys())
        except (json.decoder.JSONDecodeError, aiohttp.client_exceptions.ContentTypeError):
            raise ThirdPartyApiException(
                f'{self.api_provider_name} non-JSON response: Res [{res.status}] ({res}): {response_cleaned}')
        else:
            if not response_cleaned:
                raise AccountIsPrivate()
            return response_cleaned


class RapidAPIClient(BaseThirdPartyAPIClient):
    api_provider_name = 'Rapid API'
    headers = {
        'x-rapidapi-host': settings.RAPIDAPI_EDGE,
        'x-rapidapi-key': settings.RAPIDAPI_KEY,
    }

    async def get_user_stories(self, username: str) -> list:
        res = await self.request(
            edge='user/stories',
            querystring={'username': username},
            url=settings.RAPIDAPI_URL,
        )
        return res

    async def get_selected_reel(self, reel_id: str) -> list:
        res = await self.request(
            edge='post/info',
            querystring={'post': f"https://www.instagram.com/p/{reel_id}/"},
            url=settings.RAPIDAPI_URL,
        )
        return [res]

    async def get_selected_story(self, username: str, story_id: str) -> list:
        # iterate over stories list to find story by id
        for story in await self.get_user_stories(username):
            if story['pk'] == story_id:
                return [story]
            log.debug(f'pk: {story["pk"]}, story_id:{story_id}')

        return []
