import asyncio_redis
import enum
import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any, Optional

import settings
from common.models import AutoNameEnum


log = logging.getLogger(__name__)


class StashKeys(AutoNameEnum):
    """
    Allowed keys for Redis storage.
    """
    conversation = enum.auto()
    user_requests = enum.auto()
    user_paid_requests = enum.auto()


class RedisConnector():
    _connection = None
    _skippable_keys = [
        'conversation',
        'flood_wait_until',
        'hashtags_cloud',
        'user_paid_requests',
        'user_requests',
    ]

    @property
    async def connection(self):
        if not self._connection:
            self._connection = await asyncio_redis.Connection.create(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
            )
            log.debug('Created connection for Redis:\n%s:%s', settings.REDIS_HOST, settings.REDIS_PORT)
        return self._connection

    async def delete_data(self, key: str) -> None:
        if isinstance(key, enum.Enum):
            key = key.value
        await (await self.connection).delete([key])

    async def get_data(self, key: str) -> Optional[Any]:
        if isinstance(key, enum.Enum):
            key = key.value
        if (saved_state := await (await self.connection).get(key)):
            return json.loads(saved_state)
        if not any(filter(lambda sk: sk in key, self._skippable_keys)):
            log.warning('No saved data for key %s', key)

    async def save_data(self, key: str, data: Any) -> None:
        if isinstance(key, enum.Enum):
            key = key.value
        await (await self.connection).set(key, json.dumps(
            asdict(data) if is_dataclass(data) else data, default=str))

    # shortcuts for per-user data
    async def get_user_data(self, key: str, user_id: int = 0) -> Any:
        if isinstance(key, enum.Enum):
            key = key.value
        return await self.get_data(key=f'{user_id}_{key}')

    async def save_user_data(self, key: str, data: Any, user_id: int = 0) -> None:
        if isinstance(key, enum.Enum):
            key = key.value
        await self.save_data(key=f'{user_id}_{key}', data=data)

    async def delete_user_data(self, key: str, user_id: int = 0) -> None:
        if isinstance(key, enum.Enum):
            key = key.value
        await self.delete_data(key=f'{user_id}_{key}')


redis_connector = RedisConnector()
