from helpers.base import BaseHelper
from helpers.instagram import InstagramSelectedUserStoryParserHelper, InstagramUserStoriesParserHelper, \
    InstagramSelectedReelParserHelper


def get_helper_class_from_link(text: str) -> BaseHelper:
    if '/stories/' in text:
        return InstagramSelectedUserStoryParserHelper
    elif '/reel/' in text:
        return InstagramSelectedReelParserHelper
    else:
        return InstagramUserStoriesParserHelper


def extract_username_from_link(link: str) -> str:
    # in reels links - no username
    if '/reel/' in link:
        return link
    if '/stories/' in link:
        return link.strip().strip('/').split('/')[-2]
    return link.strip().strip('/').split('/')[-1]