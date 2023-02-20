import datetime
import logging
from typing import Optional

from aiopg.sa import create_engine
from sqlalchemy import (
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql.expression import func

import settings

from db.models import user_table


log = logging.getLogger(__name__)


# TODO add decorator for exeptions
class DatabaseConnector():
    _engine = None
    _connection = None

    @property
    async def engine(self):
        if not self._engine:
            self._engine = await create_engine(
                user=settings.DB_USER,
                database=settings.DB_NAME,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                password=settings.DB_PASSWORD,
            )
            log.debug('Created engine for DB:\n%s:%s', settings.DB_HOST, settings.DB_PORT)
        return self._engine

    async def store_or_update_user(self, user_id: int, chat_id: int,
                                   firstname: str, lastname: str, username: str,
                                   utm: list = []) -> None:

        query_values = dict(
            firstname=firstname,
            lastname=lastname,
            username=username,
            chat_id=chat_id,
            user_id=user_id,
            blocked=False,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )
        # store utm only if it's not empty
        if utm:
            query_values['utm'] = utm
            query_values['utm_created_at'] = datetime.datetime.now()

        insert_query = insert(user_table).values(**query_values)

        updatetable_values = dict(
            firstname=firstname,
            lastname=lastname,
            blocked=False,
            updated_at=datetime.datetime.now(),
        )
        # update utm only if it's not empty
        if utm:
            updatetable_values['utm'] = utm
            updatetable_values['utm_created_at'] = datetime.datetime.now()

        update_query = insert_query.on_conflict_do_update(
            constraint='users_user_id_username_key',
            set_=updatetable_values,
        )

        async with (await self.engine).acquire() as connection:
            await connection.execute(update_query)

    async def save_user_paid_requests_count(self, user_id: int, requests_count: int) -> None:
        query = update(user_table)\
            .where(user_table.c.user_id == user_id)\
            .values(paid_requests_count=user_table.c.paid_requests_count + requests_count)

        async with (await self.engine).acquire() as connection:
            await connection.execute(query)

    async def user_toggle_announce(self, user_id: int, state: bool) -> None:
        query = update(user_table)\
            .where(user_table.c.user_id == user_id)\
            .values(announce_allowed=state)

        async with (await self.engine).acquire() as connection:
            await connection.execute(query)

    async def user_toggle_block(self, user_id: int, state: bool = True) -> None:
        query = update(user_table)\
            .where(user_table.c.user_id == user_id)\
            .values(blocked=state)

        async with (await self.engine).acquire() as connection:
            await connection.execute(query)

    async def user_was_announced(self, user_id: int, date: Optional[datetime.datetime] = None) -> None:
        if not date:
            date = datetime.datetime.now()

        query = update(user_table)\
            .where(user_table.c.user_id == user_id)\
            .values(last_announced=date)

        async with (await self.engine).acquire() as connection:
            await connection.execute(query)

    # TODO make one query + dataclass with properties
    async def get_users_count(self) -> int:
        query = select(func.count())\
            .select_from(user_table)\
            .where(~user_table.c.blocked)

        async with (await self.engine).acquire() as connection:
            return await (await connection.execute(query)).scalar()

    async def get_users_count_all(self) -> int:
        query = select(func.count())\
            .select_from(user_table)\

        async with (await self.engine).acquire() as connection:
            return await (await connection.execute(query)).scalar()

    async def get_user_ids_for_announce(self) -> int:
        query = select(user_table.c.user_id)\
            .where(
                (~user_table.c.blocked) &
                (user_table.c.announce_allowed) &
                (
                     (user_table.c.last_announced.is_(None)) |
                     (user_table.c.last_announced < (
                        datetime.datetime.now() - datetime.timedelta(hours=settings.ANNOUNCE_DELAY_BETWEEN_ANNOUNCES_H)
                     ))
                )
            )

        async with (await self.engine).acquire() as connection:
            res = await connection.execute(query)
            res = await res.fetchall()
            return [row[0] for row in res]

    async def get_user(self, username: str, user_id: int) -> user_table:
        query = select(user_table)\
            .where(
                (user_table.c.username == username) &
                (user_table.c.user_id == user_id)
            )

        async with (await self.engine).acquire() as connection:
            return await (await connection.execute(query)).first()


database_connector = DatabaseConnector()
