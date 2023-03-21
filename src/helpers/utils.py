from common.models import ThirdPartyAPISource
from helpers.base import BaseHelper
from helpers.clients import TikTokRapidAPIClient, InstagramRapidAPIClient
from helpers.instagram import (InstagramSelectedUserStoryParserHelper,
                               InstagramUserStoriesParserHelper,
                               InstagramSelectedReelParserHelper,
                               InstagramMusicParserHelper,
                               InstagramPostParserHelper,
                               InstagramUserHighlightsParserHelper)
from helpers.tiktok import (TikTokSelectedMusicParserHelper,
                            TikTokSelectedVideoParserHelper,
                            TikTokUnknownMediaTypeParserHelper)
from models import BotModule


def get_helper_class_from_link_instagram(text: str) -> BaseHelper:
    if '/highlights/' in text or '/s/' in text:
        return InstagramUserHighlightsParserHelper
    elif '/stories/' in text:
        return InstagramSelectedUserStoryParserHelper
    elif '/reel/' in text:
        return InstagramSelectedReelParserHelper
    elif '/audio/' in text:
        return InstagramMusicParserHelper
    elif '/p/' in text:
        return InstagramPostParserHelper
    else:
        return InstagramUserStoriesParserHelper


def get_helper_class_from_link_tiktok(text: str) -> BaseHelper:
    if '/video/' in text:
        return TikTokSelectedVideoParserHelper
    if '/music/' in text:
        return TikTokSelectedMusicParserHelper
    else:
        # for universal links: https://vt.tiktok.com/ZS8rh8oAH/
        return TikTokUnknownMediaTypeParserHelper


def get_monitoring_handler(module: BotModule, social_network: str, media_type: str) -> callable:
    if social_network == ThirdPartyAPISource.instagram.value:
        match media_type:
            case module.reels_button:
                return InstagramRapidAPIClient().get_instagram_reels_by_username
            case module.posts_button:
                return InstagramRapidAPIClient().get_instagram_posts_by_username
            case module.stories_button:
                return InstagramRapidAPIClient().get_instagram_user_stories
    else:
        return TikTokRapidAPIClient().get_tiktok_user_videos_by_username
