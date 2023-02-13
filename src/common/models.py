import datetime
import enum
import logging
import math
from dataclasses import dataclass, field

import settings


log = logging.getLogger(__name__)


class AutoNameEnum(enum.Enum):
    """
    Just like common Enum, but use names instead of numeric values.
    """
    def _generate_next_value_(name, start, count, last_values):
        return name

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

    def __hash__(self):
        # required to be usable as dict key e.g. for serializer field choices
        return hash(self._name_)


@dataclass
class MessagePreferences:
    markdown: bool = field(default=True)
    notification: bool = field(default=False)
    link_preview: bool = field(default=True)


@dataclass
class AnnouncePreferences(MessagePreferences):
    pack_length: float = field(default=settings.ANNOUNCE_PACK_LENGTH)


@dataclass
class AnnounceJobStats:
    started_at: str = field(default='')

    # stats
    blocked: int = field(default=0)
    failed: int = field(default=0)
    success: int = field(default=0)
    total: int = field(default=0)  # quantity of users announce will be sent to

    @property
    def spent_time_s(self) -> int:
        return (
            datetime.datetime.now() - datetime.datetime.strptime(self.started_at, settings.DATE_FORMAT)
        ).seconds

    @property
    def spent_time_m(self) -> int:
        return self.spent_time_s // 60

    @property
    def rate(self) -> int:
        rate = 60 * (self.sent / self.spent_time_s) if self.spent_time_s else 0
        return round(rate, 2)

    @property
    def sent(self) -> int:
        return self.success + self.blocked + self.failed

    @property
    def eta(self) -> datetime.datetime:
        return datetime.datetime.now() + datetime.timedelta(
            seconds=((self.total - self.sent) // self.rate if self.rate else 0)
        )


@dataclass(frozen=True)
class Hashtag:
    """
    Defines hashtag representation with some useful shortcuts.
    """
    rate: int = field(default=0)
    text: str = field(default_factory=str)

    @property
    def humanized_rate(self) -> str:
        millnames = ['', 'K', 'M', 'B', 'T']

        n = float(self.rate)
        millidx = max(0, min(len(millnames)-1,
                             int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

        return '{:.0f}{}'.format(n / 10**(3 * millidx), millnames[millidx])

    @property
    def rate_category(self):
        for category, rate_threshold in settings.HASHTAGS_RATE_THRESHOLD.items():
            if self.rate >= rate_threshold:
                return category

    def __str__(self):
        if self.rate:
            return f'{self.text} - {self.humanized_rate}'

        return self.text


@dataclass
class ChannelStats:
    publications: int

    subscribers: int
    subscribers_delta_today: int
    subscribers_delta_month: int
    subscribers_delta_week: int

    citation_index: float

    average_single_publication_views: int
    average_single_publication_ad_views: int
    average_single_publication_ad_views_12h: int
    average_single_publication_ad_views_24h: int
    average_single_publication_ad_views_48h: int

    average_interest: float
    average_interest_daily: float

    channel_age_days: int
    channel_created_at: datetime.datetime


"""
  подписчики: 11 425

  сегодня: -3
  за неделю: -6
  за месяц: +119


индекс цитирования: 11.6



средний охват1 публикации: 2 456

  ERR: 21.5%
  ERR24: 10.3%


средний рекламныйохват 1 публикации: 1 174

  за 12 часов: 804
  за 24 часа: 1.2k
  за 48 часов: 1.4k


возраст канала: 6 лет 11 месяцев

  канал создан: 28.09.2015
  добавлен в TGStat: 19.07.2017


публикации: 3 561всего



вовлеченность подписчиков (ERR): 22%
"""


@dataclass(frozen=True)
class Post:
    """
    Defines user post in social network feed.
    """
    comments_count: int
    created_at: datetime.datetime
    likes_count: int
    link: str
    owner_id: int

    @property
    def activity_count(self):
        return self.comments_count + self.likes_count


class ProxyUsage(enum.IntEnum):
    """
    Defines available purposes of proxy usage.
    This class is a part of eponymous class from
    smp-client-instagram.
    """
    ig_get_tag_edges = 24
    ig_search_tags = 25


@dataclass(frozen=True)
class SmmCard:
    link: str
    text: str
    title: str

    @property
    def utm_campaign(self):
        parts = self.link.split('/')
        return parts[-1] or parts[-2]  # workaround links ending with /

    @property
    def utm_link(self):
        return f'{self.link}?utm_source=telegram&utm_medium=bot&utm_campaign={self.utm_campaign}'


class UserRoleBit(enum.IntEnum):
    """
    Defines available roles for the Bot users.
    Unix-like bit model is used:
    - 001 - admin
    - 010 - content creator
    - 100 - spectator
    ...
    """
    admin = 0  # can assign other roles
    manager = 1  # can perform announces
    content_creator = 2  # can add/delete smm cards
    spectator = 3  # can get statistics
