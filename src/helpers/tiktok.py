import logging

from exceptions import WrongInputException
from .base import BaseHelper
import validators

log = logging.getLogger(__name__)


class TikTokSelectedVideoParserHelper(BaseHelper):
    _search_method = 'get_tiktok_video'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://www.tiktok.com/@xxx/video/6988865319091703042?lang=ru-RU
        """
        if not (text := self._message.text) or not validators.url(self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        return [text]

    def __str__(self):
        return 'tiktok_video_parser'


class TikTokSelectedMusicParserHelper(BaseHelper):
    _search_method = 'get_tiktok_music'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://www.tiktok.com/@xxx/music/6988865319091703042?lang=ru-RU
        """
        if not (text := self._message.text) or not validators.url(self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        return [text]

    def __str__(self):
        return 'tiktok_music_parser'


class TikTokUnknownMediaTypeParserHelper(BaseHelper):
    _search_method = 'get_tiktok_unknown_media'

    @property
    def keyword(self):
        """
        links can be in forms of:
            https://vt.tiktok.com/ZS8rrTJag/
        """
        if not (text := self._message.text) or not validators.url(self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        return [text]

    def __str__(self):
        return 'tiktok_unknown_media_parser'
