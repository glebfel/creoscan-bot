import logging

from exceptions import WrongInputException
from .base import BaseHelper

log = logging.getLogger(__name__)


class InstagramUserStoriesParserHelper(BaseHelper):
    _search_method = 'get_user_stories'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://instagram.com/nickname
            @nickname
            nickname
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # extract username
        text = text.strip().strip('/').split('/')[-1]

        # return list because of unpacking args process
        return [text.replace('@', '')]

    def __str__(self):
        return 'instagram_user_stories_parser'


class InstagramSelectedUserStoryParserHelper(BaseHelper):
    _search_method = 'get_selected_story'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://instagram.com/stories/mozgslomal/3007657127355045430?utm_source=ig_story_item_share&igshid=YmMyMTA2M2Y=
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # extract username and story id
        text = text.strip().strip('/')
        story_id = text.split('/')[-1]
        username = text.split('/')[-2]

        return username, story_id

    def __str__(self):
        return 'instagram_selected_user_story_parser'


class InstagramSelectedReelParserHelper(BaseHelper):
    _search_method = 'get_selected_reel'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://www.instagram.com/reel/CmrETDDKGLf/?igshid=YmMyMTA2M2Y=
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # extract username and story id
        text = text.strip().strip('/')
        reel_id = text.split('/')[-1]

        # return list because of unpacking args process
        return [reel_id]

    def __str__(self):
        return 'instagram_selected_user_story_parser'
