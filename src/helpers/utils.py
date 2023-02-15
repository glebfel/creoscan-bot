from helpers.base import BaseHelper
from helpers.instagram import InstagramSelectedUserStoryParserHelper, InstagramUserStoriesParserHelper


def get_helper_class_from_link(text: str) -> BaseHelper:
    if '/stories/' in text:
        return InstagramSelectedUserStoryParserHelper
    elif '/reels/' in text:
        pass
    else:
        return InstagramUserStoriesParserHelper


def extract_username_from_link(link: str) -> str:
    if '/reels/' in link:
        return link
    if '/stories/' in link:
        return link.strip().strip('/').split('/')[-2]
    return link.strip().strip('/').split('/')[-1]