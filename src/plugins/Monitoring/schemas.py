import datetime
from dataclasses import dataclass, field


@dataclass
class UserMonitoringRequest:
    user_id: int
    nickname: str = None
    social_network: str = None
    active: bool = None
    selected_media_type: str | None = None
    start_date: datetime.datetime = field(default=datetime.datetime.now())
    is_confirmed: bool = None