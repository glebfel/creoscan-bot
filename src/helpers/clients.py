import datetime
import json
import logging

import aiohttp

import settings
from common.models import Hashtag, Post
from exceptions import (
    AccountIsPrivate,
    AccountNotExist,
    EmptyResultsException,
    ThirdPartyApiException,
    ThirdPartyTimeoutError,
)
from .utils import (
    fix_hashtag_text,
    get_hashtags_from_text,
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
                log.debug('Json response: %s', response_cleaned.keys())
        except (json.decoder.JSONDecodeError, aiohttp.client_exceptions.ContentTypeError):
            raise ThirdPartyApiException(
                f'{self.api_provider_name} non-JSON response: Res [{res.status}] ({res}): {response_cleaned}')
        else:
            if not response_cleaned:
                raise EmptyResultsException(
                    f'Empty {self.api_provider_name} response. Res [{res.status}] ({res}): {response_cleaned}')
            return response_cleaned


class HashtagsExtractorMixin:
    async def _make_hashtags(self, raw: dict) -> list:
        try:
            hashtags = [await self._make_hashtag(h) for h in raw]
            return hashtags
        except TypeError as exc:
            raise Exception(f'Failed to convert {raw} to Hashtags: {exc}')


class RapidAPIClient(BaseThirdPartyAPIClient, HashtagsExtractorMixin):
    api_provider_name = 'Rapid API'
    headers = {
        'x-rapidapi-host': settings.RAPIDAPI_EDGE,
        'x-rapidapi-key': settings.RAPIDAPI_KEY,
    }

    # TODO
    '''
    request_limit = int(res.headers.get('X-RateLimit-Requests-Limit', 1))
    request_remain = int(res.headers.get('X-RateLimit-Requests-Remaining', 1))

    if (request_remain * 100) / request_limit < 30:
        notify_admin(f'RapidAPI limit close to exceeding, remain {request_remain} of {request_limit}')
    '''

    async def get_hashtags_by_word(self, word: str) -> list:
        res = await self.request(
            edge='hashtag/search',
            querystring={'keyword': word},
            url=settings.RAPIDAPI_URL,
        )
        raw_hashtags = res['hashtags']
        if not isinstance(raw_hashtags, list):
            raise ThirdPartyApiException('Failed to extract hashtags: %s', raw_hashtags)
        return await self._make_hashtags(raw=raw_hashtags)

    async def _get_user_feed(self, username: str) -> list:
        res = await self.request(
            edge='user/feed',
            querystring={'username': username},
            url=settings.RAPIDAPI_URL,
        )
        """
        {
            'count': 543,
            'has_more': True,
            'end_cursor': 'QVFCZnJxa2dhX0JIaHBuQTR4cHhpNjhER2tmTUZTT0U5QkIxcVJ1dEl0bm56TVNSQXR3R09sT1M5RlpWOFNFd0RQZ3Yza3I5TF9EVzBNNS1jbkdKc1o3aA==',  # noqa
            'collector': [
                {
                    'id': '2788646709112433828',
                    'shortcode': 'CazQ2g0tWyk',
                    'type': 'GraphSidecar',
                    'is_video': False,
                    'dimension': {'height': 1350, 'width': 1080},
                    'display_url': 'https://instagram.fhrk1-1.fna.fbcdn.net/...',
                    'thumbnail_src': 'https://instagram.fhrk1-1.fna.fbcdn.net/...',
                    'owner': {'id': '1591393565', 'username': 'smmplanner'},
                    'description': '...',
                    'comments': 8,
                    'likes': 334,
                    'comments_disabled': False,
                    'taken_at_timestamp': 1646652614,
                    'location': None,
                    'hashtags': [],
                    'mentions': ['@krd_pike', '@moscow_pike', '@elvina_abibullaevaa'],
                    'tagged_users': [
                        {
                            'user': {
                                'full_name': 'John Doe',
                                'id': '224339966',
                                'is_verified': False,
                                'profile_pic_url': 'https://instagram.fhrk1-1.fna.fbcdn.net/v/t51.2885-19/248678456_1221145015059318_3460660294581867683_n.jpg?stp=dst-jpg_s150x150&_nc_ht=instagram.fhrk1-1.fna.fbcdn.net&_nc_cat=106&_nc_ohc=RkL63rxKBr4AX96d9Oc&edm=APU89FABAAAA&ccb=7-4&oh=00_AT-TNPcH_DgP_WZ1KZ1MryohxnmdhRVLlXa7oTVQvxcCkA&oe=6230327E&_nc_sid=86f79a',
                                'username': 'elvina_abibullaevaa'
                            },
                            'x': 0.6751207729,
                            'y': 0.7367149758
                        }
                    ]
                }
            ]
        }
        """
        if res.get('count') and not res.get('collector'):
            raise AccountIsPrivate(username)

        if not res.get('count') and not res.get('collector'):
            raise AccountNotExist(username)

        return res

    async def get_hashtags_from_feed(self, username: str) -> list:
        res = await self._get_user_feed(username)

        hashtags = []

        for post in res.get('collector', []):
            raw_hashtags = post['hashtags']
            if isinstance(raw_hashtags, list):
                hashtags.extend(raw_hashtags)
            else:
                log.warning('Failed to extract hashtags: %s', raw_hashtags)
            hashtags.extend(await get_hashtags_from_text(post.get('description', '')))

        return [
            Hashtag(
                text=await fix_hashtag_text(h),
            ) for h in set(hashtags)
        ]

    async def get_posts_from_feed(self, username: str) -> list:
        res = await self._get_user_feed(username)
        return [
            Post(
                comments_count=p['comments'],
                created_at=datetime.datetime.fromtimestamp(p['taken_at_timestamp']),
                link=f'https://www.instagram.com/p/{p["shortcode"]}/',
                likes_count=p['likes'],
                owner_id=p['owner']['id'],
            ) for p in res.get('collector', [])
        ]

    @staticmethod
    async def _make_hashtag(raw: dict) -> Hashtag:
        """
        [
            {
                "position": 1,
                "hashtag": {
                    "name": "moscow",
                    "id": 17843723539051693,
                    "media_count": 58817581,
                    "use_default_avatar": false,
                    "profile_pic_url": "https://www.instagram.com/static/...",
                    "search_result_subtitle": "58.8m posts"
                }
            },
        ]
        """
        return Hashtag(
            rate=raw['hashtag'].get('media_count', 0),
            text=await fix_hashtag_text(raw['hashtag']['name']),
        )
