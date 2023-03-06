import datetime
import enum
import logging
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


class ThirdPartyAPIMediaType(enum.IntEnum):
    """
    Defines available media types from third party APIs.
    """
    unknown = 0
    photo = 1
    video = 2
    audio = 3


class ThirdPartyAPISource(AutoNameEnum):
    """
    Defines available media types from third party APIs.
    """
    instagram = 'ig'
    tiktok = 'tt'


@dataclass
class ThirdPartyAPIMediaItem:
    media_type: ThirdPartyAPIMediaType = field(default=ThirdPartyAPIMediaType.unknown)
    media_url: str = field(default='')
    media_id: str = field(default='')


@dataclass
class ThirdPartyAPIClientAnswer:
    source: ThirdPartyAPISource
    items: list[ThirdPartyAPIMediaItem] = field(default_factory=list)
