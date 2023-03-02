import asyncio
import datetime
import logging

import tortoise
from tortoise import Tortoise
from tortoise.expressions import Q

import settings
from db.models import Users

log = logging.getLogger(__name__)


class DatabaseConnector:
    def __init__(self):
        self._sync_init()

    async def _async_init(self):
        await Tortoise.init(
            db_url=f'asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}',
            modules={'models': ['db.models']},
        )
        # Generate the schema
        # safe=True - generate schema if not exists in db
        await Tortoise.generate_schemas(safe=True)

    def _sync_init(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_init())

    async def store_or_update_user(self, user_id: int, chat_id: int,
                                   firstname: str, lastname: str, username: str,
                                   utm: list = None) -> None:

        query_values = dict(
            firstname=firstname,
            lastname=lastname,
            username=username,
            chat_id=chat_id,
            user_id=user_id,
            blocked=False,
            created_at=tortoise.timezone.now(),
            updated_at=tortoise.timezone.now(),
        )
        # store utm only if it's not empty
        if utm:
            query_values['utm'] = utm
            query_values['utm_created_at'] = tortoise.timezone.now()

        await Users.bulk_create(objects=[Users(**query_values)], on_conflict=['user_id'],
                                update_fields=['firstname', 'lastname',
                                               'blocked', 'updated_at',
                                               'utm', 'utm_created_at'])


    async def save_user_paid_requests_count(self, user_id: int, requests_count: int) -> None:
        await Users.filter(user_id=user_id).update(paid_requests_count=+ requests_count)

    async def user_toggle_announce(self, user_id: int, state: bool) -> None:
        await Users.filter(user_id=user_id).update(announce_allowed=state)

    async def user_toggle_block(self, user_id: int, state: bool = True) -> None:
        await Users.filter(user_id=user_id).update(blocked=state)

    async def user_was_announced(self, user_id: int, date: datetime.datetime = None) -> None:
        if not date:
            date = tortoise.timezone.now()

        await Users.filter(user_id=user_id).update(last_announced=date)

    async def get_users_count(self) -> int:
        return await Users.filter(blocked=False).all().count()

    async def get_users_count_all(self) -> int:
        return await Users.all().count()

    async def get_user(self, username: str, user_id: int) -> Users:
        return await Users.filter(Q(username=username) & Q(user_id=user_id)).first()


database_connector = DatabaseConnector()
