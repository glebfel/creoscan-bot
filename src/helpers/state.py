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


class RedisConnector:
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


class UserMonitoringRequests:
    """
    Handle user's monitoring requests using redis.
    """

    @staticmethod
    async def save_user_request(user_id: int, new=False, **kwargs) -> None:
        if new:
            request_list = await redis_connector.get_data(key=str(user_id))
            if not request_list:
                await redis_connector.save_data(key=str(user_id), data=[kwargs])
            else:
                request_list.append(kwargs)
                await redis_connector.save_data(key=str(user_id), data=request_list)
        else:
            request_list = await redis_connector.get_data(key=str(user_id))
            request_list[-1].update(kwargs)
            await redis_connector.save_data(key=str(user_id), data=request_list)

    @staticmethod
    async def get_last_user_request(user_id: int) -> dict:
        requests = await redis_connector.get_data(key=str(user_id))
        if requests:
            return requests[-1]

    @staticmethod
    async def get_user_requests(user_id: int) -> list[dict]:
        requests = await redis_connector.get_data(key=str(user_id))
        if not requests:
            return []
        return requests

    @staticmethod
    async def get_user_request_by_nickname_and_social(user_id: int, social_network: str, nickname: str) -> dict | None:
        requests = await UserMonitoringRequests.get_user_requests(user_id)
        for _ in requests:
            if _['social_network'] == social_network and _['nickname'] == nickname:
                return _

    @staticmethod
    async def delete_user_request_by_nickname_and_social(user_id: int, social_network: str, nickname: str) -> None:
        requests = await UserMonitoringRequests.get_user_requests(user_id)
        for _ in requests:
            if _['social_network'] == social_network and _['nickname'] == nickname:
                return requests.remove(_)
        await redis_connector.save_data(key=str(user_id), data=requests)

    @staticmethod
    async def get_user_requests_count(user_id: int) -> int:
        return len(await UserMonitoringRequests.get_user_requests(user_id))


redis_connector = RedisConnector()
