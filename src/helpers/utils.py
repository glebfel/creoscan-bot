from helpers.base import BaseHelper
from helpers.instagram import InstagramSelectedUserStoryParserHelper, InstagramUserStoriesParserHelper, \
    InstagramSelectedReelParserHelper
from helpers.tiktok import TikTokSelectedMusicParserHelper, TikTokSelectedVideoParserHelper, TikTokUnknownMediaTypeParserHelper


def get_helper_class_from_link_instagram(text: str) -> BaseHelper:
    if '/stories/' in text:
        return InstagramSelectedUserStoryParserHelper
    elif '/reel/' in text:
        return InstagramSelectedReelParserHelper
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


def extract_username_from_link_instagram(link: str) -> str:
    # in reels links - no username
    if '/reel/' in link:
        return link
    if '/stories/' in link:
        return link.strip().strip('/').split('/')[-2]
    return link.strip().strip('/').split('/')[-1]