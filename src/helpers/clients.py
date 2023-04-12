import datetime
import json
import logging

import aiohttp

import exceptions
import settings
from common.models import ThirdPartyAPIClientAnswer, ThirdPartyAPIMediaType, ThirdPartyAPIMediaItem, ThirdPartyAPISource
from exceptions import (
    AccountIsPrivate,
    AccountNotExist,
    EmptyResultsException,
    ThirdPartyApiException,
    ThirdPartyTimeoutError,
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

    async def get_instagram_user_stories(self, username: str, limit: int = None) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='user/stories',
            querystring={'username': username},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        # all stories in list is located chronologically (first element is the earliest)
        # so we need to reverse it
        raw_data.reverse()

        items = []
        for ind, media in enumerate(raw_data):
            if ind == limit:
                break
            match media['media_type']:
                case 1:
                    items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.photo,
                                                        media_id=media['pk'],
                                                        media_url=media['image_versions2']['candidates'][0]['url'],
                                                        taken_at=datetime.datetime.fromtimestamp(media['taken_at'])))
                case 2:
                    items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                                        media_id=media['pk'],
                                                        media_url=media['video_versions'][-1]['url'],
                                                        taken_at=datetime.datetime.fromtimestamp(media['taken_at'])))
        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.instagram,
            items=items,
        )

    async def get_instagram_selected_reel(self, reel_id: str) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='post/info',
            querystring={'post': f"https://www.instagram.com/p/{reel_id}/"},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        items = []
        match raw_data['media_type']:
            case 1:
                items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.photo,
                                                    media_id=raw_data['pk'],
                                                    media_url=raw_data['image_versions2']['candidates'][0]['url']))
            case 2:
                items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                                    media_id=raw_data['pk'],
                                                    media_url=raw_data['video_versions'][-1]['url']))
        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.instagram,
            items=items,
        )

    async def get_instagram_post(self, post_id: str) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='post/info',
            querystring={'post': f"https://www.instagram.com/p/{post_id}/"},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        items = []
        match raw_data['media_type']:
            case 1:
                items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.photo,
                                                    media_id=raw_data['pk'],
                                                    media_url=raw_data['image_versions2']['candidates'][0]['url']))
            case 2:
                items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                                    media_id=raw_data['pk'],
                                                    media_url=raw_data['video_versions'][-1]['url']))
            case 8:
                # carousel media
                for media in raw_data['carousel_media']:
                    match media['media_type']:
                        case 1:
                            items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.photo,
                                                                media_id=media['pk'],
                                                                media_url=
                                                                media['image_versions2']['candidates'][0][
                                                                    'url']))
                        case 2:
                            items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                                                media_id=media['pk'],
                                                                media_url=media['video_versions'][-1]['url']))
        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.instagram,
            items=items,
        )

    async def get_instagram_posts_by_username(self, username: str, limit: int = None) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='user/feed/v2',
            querystring={'username': username},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        items = []
        for ind, post in enumerate(raw_data['items']):
            if ind == limit:
                break
            match post['media_type']:
                case 1:
                    items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.photo,
                                                        media_id=post['pk'],
                                                        media_url=post['image_versions2']['candidates'][0]['url'],
                                                        taken_at=datetime.datetime.fromtimestamp(post['taken_at'])))
                case 2:
                    items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                                        media_id=post['pk'],
                                                        media_url=post['video_versions'][-1]['url'],
                                                        taken_at=datetime.datetime.fromtimestamp(post['taken_at'])))
                case 8:
                    # carousel media
                    for media in post['carousel_media']:
                        match media['media_type']:
                            case 1:
                                items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.photo,
                                                                    media_id=media['pk'],
                                                                    media_url=media['image_versions2']['candidates'][0]['url'],
                                                                    taken_at=datetime.datetime.fromtimestamp(post['taken_at'])))
                            case 2:
                                items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                                                    media_id=media['pk'],
                                                                    media_url=media['video_versions'][-1]['url'],
                                                                    taken_at=datetime.datetime.fromtimestamp(post['taken_at'])))
        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.instagram,
            items=items,
        )

    async def get_instagram_reels_by_username(self, username: str, limit: int = None) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='user/reels',
            querystring={'username': username, 'limit': str(limit)},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        items = []
        for ind, reel in enumerate(raw_data['items']):
            if ind == limit:
                break
            match reel['media_type']:
                case 1:
                    items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.photo,
                                                        media_id=reel['pk'],
                                                        media_url=reel['image_versions2']['candidates'][0]['url'],
                                                        taken_at=datetime.datetime.fromtimestamp(reel['taken_at'])))
                case 2:
                    items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                                        media_id=reel['pk'],
                                                        media_url=reel['video_versions'][-1]['url'],
                                                        taken_at=datetime.datetime.fromtimestamp(reel['taken_at'])))
        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.instagram,
            items=items,
        )

    async def get_instagram_user_highlights(self, highlight_url: str) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='user/stories/highlights',
            querystring={"url": highlight_url},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        items = []
        # extract highlight id
        highlight_id = highlight_url.split('?')[0].strip('/').split('/')[-1]
        for story in raw_data['reels'][f'highlight:{highlight_id}']['items']:
            match story['media_type']:
                case 1:
                    items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.photo,
                                                        media_id=story['pk'],
                                                        media_url=story['image_versions2']['candidates'][0]['url']))
                case 2:
                    items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                                        media_id=story['pk'],
                                                        media_url=story['video_versions'][-1]['url']))
        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.instagram,
            items=items,
        )

    async def get_instagram_selected_story(self, username: str, story_id: str) -> ThirdPartyAPIClientAnswer:
        # iterate over stories list to find story by id
        for story in (await self.get_instagram_user_stories(username)).items:
            log.debug(f'pk: {story.media_id}, story_id:{story_id}')
            if story.media_id == story_id:
                return ThirdPartyAPIClientAnswer(
                    source=ThirdPartyAPISource.instagram,
                    items=[story],
                )
        # if stories not found
        raise EmptyResultsException()

    async def get_instagram_music(self, music_id: str) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='audio/feed',
            querystring={"audio_id": music_id},
            url=settings.INSTAGRAM_RAPIDAPI_URL,
        )
        # extract download url
        if not (music_url := raw_data['metadata']['original_sound_info']):
            if not (music_url := raw_data['metadata']['music_info']['music_asset_info']['progressive_download_url']):
                raise EmptyResultsException()
        else:
            music_url = music_url['progressive_download_url']

        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.instagram,
            items=[ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.audio,
                                          media_id=music_id,
                                          media_url=music_url)]
        )


class TikTokRapidAPIClient(BaseThirdPartyAPIClient):
    api_provider_name = 'Rapid API'
    headers = {
        'x-rapidapi-host': settings.TIKTOK_RAPIDAPI_EDGE,
        'x-rapidapi-key': settings.TIKTOK_RAPIDAPI_KEY,
    }

    async def get_tiktok_user_videos_by_username(self, username, limit: int = None) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='user/posts',
            querystring={"unique_id": username},
            url=settings.TIKTOK_RAPIDAPI_URL,
        )
        if raw_data['code'] == -1:
            raise EmptyResultsException()

        items = []
        for ind, video in enumerate(raw_data['data']['videos']):
            if ind == limit:
                break
            items.append(ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                                media_url=video['play'],
                                                taken_at=datetime.datetime.fromtimestamp(video['create_time'])))

        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.tiktok,
            items=items
        )

    async def get_tiktok_video(self, url: str, unknown_media: bool = False) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='',
            querystring={"url": url},
            url=settings.TIKTOK_RAPIDAPI_URL,
        )
        if raw_data['code'] == -1:
            if unknown_media:
                return ThirdPartyAPIClientAnswer(source=ThirdPartyAPISource.tiktok)
            raise EmptyResultsException()

        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.tiktok,
            items=[ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.video,
                                          media_url=raw_data['data']['play'])]
        )

    async def get_tiktok_music(self, url: str, unknown_media: bool = False) -> ThirdPartyAPIClientAnswer:
        raw_data = await self.request(
            edge='music/info',
            querystring={"url": url},
            url=settings.TIKTOK_RAPIDAPI_URL,
        )
        if raw_data['code'] == -1:
            if unknown_media:
                return ThirdPartyAPIClientAnswer(source=ThirdPartyAPISource.tiktok)
            raise EmptyResultsException()

        return ThirdPartyAPIClientAnswer(
            source=ThirdPartyAPISource.tiktok,
            items=[ThirdPartyAPIMediaItem(media_type=ThirdPartyAPIMediaType.audio,
                                          media_url=raw_data['data']['play'])]
        )

    async def get_tiktok_unknown_media(self, url: str) -> ThirdPartyAPIClientAnswer:
        if not (res := await self.get_tiktok_video(url, unknown_media=True)).items:
            if not (res := await self.get_tiktok_music(url, unknown_media=True)).items:
                raise exceptions.WrongInputException(url)
        return res
