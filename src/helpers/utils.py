import validators
from pyrogram.types import (
    Message,
)

from exceptions import WrongInputException
from helpers.base import BaseHelper
from helpers.instagram import (InstagramSelectedUserStoryParserHelper,
                               InstagramUserStoriesParserHelper,
                               InstagramSelectedReelParserHelper,
                               InstagramMusicParserHelper,
                               InstagramPostParserHelper,
                               InstagramUserHighlightsParserHelper)
from helpers.tiktok import (TikTokSelectedMusicParserHelper,
                            TikTokSelectedVideoParserHelper,
                            TikTokUnknownMediaTypeParserHelper)


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


def extract_username_from_link(message: Message) -> str:
    if not (link := message.text) or not validators.url(message.text):
        raise WrongInputException(message.text or message.media)
    return '@' + link.strip('/').split('/')[-1].replace('@', '').split('?')[0]
