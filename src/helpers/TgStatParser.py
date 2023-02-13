import logging

from .base import BaseHelper


log = logging.getLogger(__name__)


class TgChannelParserHelper(BaseHelper):
    _search_method = 'get_channel_stats'

    @property
    def keyword(self):
        """
        account can be in forms of:
            https://t.me/smmplanner
            basni.krylova
            @basni.krylova
        """
        if not (text := self._message.text):
            raise WrongInputException(self._message.text or self._message.media)

        # cut last part if account is in form of url (and drop last /)
        text = text.split('/')[-1] or text.split('/')[-2]
        # cut utm
        text = text.split('?')[0]
        # cut '@'
        return text.replace('@', '')

    def __str__(self):
        return 'tgstat_parser'


class TgChannelPostsParser(TgChannelParserHelper):
    _search_method = 'get_channel_posts'
