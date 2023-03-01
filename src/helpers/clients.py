import json
import logging

import aiohttp

import exceptions
import settings
from common.models import ThirdPartyAPIClientAnswer, ThirdPartyAPIMediaType
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


class InstagramRapidAPIClient(BaseThirdPartyAPIClient):
    api_provider_name = 'Rapid API'
    headers = {
        'x-rapidapi-host': settings.INSTAGRAM_RAPIDAPI_EDGE,
        'x-rapidapi-key': settings.INSTAGRAM_RAPIDAPI_KEY,
    }

    async def get_user_stories(self, username: str) -> list[ThirdPartyAPIClientAnswer]:
        raw_data = await self.request(
            edge='user/stories',
            querystring={'username': username},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )

        answer = []
        for media in raw_data:
            match media['media_type']:
                case 1:
                    answer.append(ThirdPartyAPIClientAnswer(media_type=ThirdPartyAPIMediaType.photo,
                                                            media_id=media['pk'],
                                                            media_url=media['image_versions2']['candidates'][0]['url']))
                case 2:
                    answer.append(ThirdPartyAPIClientAnswer(media_type=ThirdPartyAPIMediaType.video,
                                                            media_id=media['pk'],
                                                            media_url=media['video_versions'][0]['url']))
        return answer

    async def get_selected_reel(self, reel_id: str) -> list[ThirdPartyAPIClientAnswer]:
        raw_data = await self.request(
            edge='post/info',
            querystring={'post': f"https://www.instagram.com/p/{reel_id}/"},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        answer = []
        match raw_data['media_type']:
            case 1:
                answer.append(ThirdPartyAPIClientAnswer(media_type=ThirdPartyAPIMediaType.photo,
                                                        media_id=raw_data['pk'],
                                                        media_url=raw_data['image_versions2']['candidates'][0]['url']))
            case 2:
                answer.append(ThirdPartyAPIClientAnswer(media_type=ThirdPartyAPIMediaType.video,
                                                        media_id=raw_data['pk'],
                                                        media_url=raw_data['video_versions'][0]['url']))
        return answer

    async def get_selected_post(self, post_id: str) -> list[ThirdPartyAPIClientAnswer]:
        raw_data = await self.request(
            edge='post/info',
            querystring={'post': f"https://www.instagram.com/p/{post_id}/"},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        answer = []
        match raw_data['media_type']:
            case 1:
                answer.append(ThirdPartyAPIClientAnswer(media_type=ThirdPartyAPIMediaType.photo,
                                                        media_id=raw_data['pk'],
                                                        media_url=raw_data['image_versions2']['candidates'][0]['url']))
            case 2:
                answer.append(ThirdPartyAPIClientAnswer(media_type=ThirdPartyAPIMediaType.video,
                                                        media_id=raw_data['pk'],
                                                        media_url=raw_data['video_versions'][0]['url']))
        return answer

    async def get_user_highlights(self, highlight_id: str) -> list[ThirdPartyAPIClientAnswer]:
        raw_data = await self.request(
            edge='user/stories/highlights',
            querystring={"url": f"https://www.instagram.com/stories/highlights/{highlight_id}/"},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        answer = []
        for story in raw_data['reels'][f'highlight:{highlight_id}']['items']:
            match story['media_type']:
                case 1:
                    answer.append(ThirdPartyAPIClientAnswer(media_type=ThirdPartyAPIMediaType.photo,
                                                            media_id=story['pk'],
                                                            media_url=story['image_versions2']['candidates'][0]['url']))
                case 2:
                    answer.append(ThirdPartyAPIClientAnswer(media_type=ThirdPartyAPIMediaType.video,
                                                            media_id=story['pk'],
                                                            media_url=story['video_versions'][0]['url']))
        return answer

    async def get_selected_story(self, username: str, story_id: str) -> list[ThirdPartyAPIClientAnswer]:
        # iterate over stories list to find story by id
        for story in await self.get_user_stories(username):
            log.debug(f'pk: {story.media_id}, story_id:{story_id}')
            if story.media_id == story_id:
                return [story]
        return []

    async def get_selected_music(self, music_id: str) -> list[ThirdPartyAPIClientAnswer]:
        raw_data = await self.request(
            edge='audio/feed',
            querystring={"audio_id": music_id},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        answer = [ThirdPartyAPIClientAnswer(media_type=ThirdPartyAPIMediaType.audio,
                                            media_id=music_id,
                                            media_url=raw_data['metadata']['original_sound_info']['progressive_download_url'])]
        return answer


class TikTokRapidAPIClient(BaseThirdPartyAPIClient):
    api_provider_name = 'Rapid API'
    headers = {
        'x-rapidapi-host': settings.TIKTOK_RAPIDAPI_EDGE,
        'x-rapidapi-key': settings.TIKTOK_RAPIDAPI_KEY,
    }

    async def get_selected_video(self, url: str) -> dict:
        res = await self.request(
            edge='',
            querystring={"url": url},
            url=settings.TIKTOK_RAPIDAPI_URL,
        )
        return res

    async def get_selected_music(self, url: str) -> dict:
        res = await self.request(
            edge='music/info',
            querystring={"url": url},
            url=settings.TIKTOK_RAPIDAPI_URL,
        )
        return res

    async def get_unknown_media(self, url: str) -> dict:
        if (res := await self.get_selected_video(url))['code'] == -1:
            if (res := await self.get_selected_music(url))['code'] == -1:
                raise exceptions.WrongInputException(url)
        return res
