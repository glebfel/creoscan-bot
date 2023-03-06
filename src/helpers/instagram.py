import logging

from exceptions import WrongInputException
from .base import BaseHelper

log = logging.getLogger(__name__)


class InstagramUserStoriesParserHelper(BaseHelper):
    _search_method = 'get_instagram_user_stories'

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
        username = text.split('?')[0].strip('/').split('/')[-1].replace('@', '')

        # return list because of unpacking args process
        return [username]

    def __str__(self):
        return 'instagram_user_stories_parser'


class InstagramSelectedUserStoryParserHelper(BaseHelper):
    _search_method = 'get_instagram_selected_story'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://instagram.com/stories/mozgslomal/3007657127355045430?utm_source=ig_story_item_share&igshid=YmMyMTA2M2Y=
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # extract username and story id
        story_id = text.split('?')[0].strip('/').split('/')[-1]
        username = text.split('?')[0].strip('/').split('/')[-2]

        return username, story_id

    def __str__(self):
        return 'instagram_selected_story_parser'


class InstagramSelectedReelParserHelper(BaseHelper):
    _search_method = 'get_instagram_selected_reel'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://www.instagram.com/reel/CmrETDDKGLf/?igshid=YmMyMTA2M2Y=
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # extract reel id
        reel_id = text.split('?')[0].strip('/').split('/')[-1]

        # return list because of unpacking args process
        return [reel_id]

    def __str__(self):
        return 'instagram_selected_reel_parser'


class InstagramMusicParserHelper(BaseHelper):
    _search_method = 'get_instagram_music'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://www.instagram.com/reels/audio/780162617153963
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # extract music id
        music_id = text.split('?')[0].strip('/').split('/')[-1]

        # return list because of unpacking args process
        return [music_id]

    def __str__(self):
        return 'instagram_music_parser'


class InstagramPostParserHelper(BaseHelper):
    _search_method = 'get_instagram_post'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://www.instagram.com/p/CpNbhT8NOP1/?utm_source=ig_web_copy_link
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # extract post id
        post_id = text.split('?')[0].strip('/').split('/')[-1]

        # return list because of unpacking args process
        return [post_id]

    def __str__(self):
        return 'instagram_post_parser'


class InstagramUserHighlightsParserHelper(BaseHelper):
    _search_method = 'get_instagram_user_highlights'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://www.instagram.com/stories/highlights/17946185029998255/
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # return list because of unpacking args process
        return [text]

    def __str__(self):
        return 'instagram_user_highlights_parser'
