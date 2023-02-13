import logging
from dataclasses import dataclass, field

from pyrogram.types import (
    CallbackQuery,
    Message,
)

import settings
from db.connector import database_connector
from helpers.state import redis_connector, StashKeys
from models import Module
from utils import check_trottling

log = logging.getLogger(__name__)


@dataclass
class TrottlingModule(Module):
    warning_message: str = field(init=False)


trottling_module = TrottlingModule('trottling')


def handle_trottling_decorator(func):
    """
    Counts user requests per given amount of time and restricts if overhead.
    """
    async def wrapper(*args, **kwargs):
        # skip calls without Update object
        if not any(isinstance(update := arg, (CallbackQuery, Message)) for arg in args):
            return await func(*args, **kwargs)

        # flake8: noqa: F821

        if not update.from_user:
            return await func(*args, **kwargs)

        stash_key = StashKeys.user_requests

        if await check_trottling(
            stash_key=stash_key,
            window_size_s=settings.TROTTLING_WAIT_BETWEEN_REQUESTS_S,
            user_id=update.from_user.id,
        ):
            await _warn_user_trottling(stash_key, update)
        else:
            await func(*args, **kwargs)

    return wrapper


def handle_paid_requests_trottling_decorator(func):
    """
    Counts user requests to paid API and stores them to DB.
    """
    async def wrapper(*args, **kwargs):
        # skip calls without Update object
        if not any(isinstance(update := arg, (CallbackQuery, Message)) for arg in args):
            return await func(*args, **kwargs)

        if not update.from_user:
            return await func(*args, **kwargs)

        stash_key = StashKeys.user_paid_requests

        if await check_trottling(
                stash_key=stash_key,
                on_counter_reset=_save_requests_count,
                window_size_s=settings.TROTTLING_WAIT_BETWEEN_PAID_REQUESTS_S,
                user_id=update.from_user.id,
        ):
            await _warn_user_trottling(stash_key, update)
        else:
            await func(*args, **kwargs)

    return wrapper


async def _save_requests_count(count: int, user_id: int) -> None:
    log.debug('Trottling window is over, dumping %s requests count to DB', count)
    await database_connector.save_user_paid_requests_count(user_id=user_id, requests_count=count)


async def _warn_user_trottling(stash_key: StashKeys, update: Message) -> None:
    if isinstance(update, Message):
        user_requests = await redis_connector.get_user_data(
            key=stash_key, user_id=update.from_user.id) or {}

        if user_requests.get('was_notified'):
            return

        await update.reply(trottling_module.warning_message)

        # set flag to avoid notifications on each trottling activation
        user_requests.update({'was_notified': True})

        await redis_connector.save_user_data(
            key=stash_key,
            data=user_requests,
            user_id=update.from_user.id,
        )
