import aiohttp
import datetime
import logging
import time

import settings
from helpers.state import redis_connector


log = logging.getLogger(__name__)


async def notify_admin(message: str) -> None:
    admin_notified_at = await redis_connector.get_data(key='admin_notified_at')

    if admin_notified_at and (
        datetime.datetime.fromtimestamp(admin_notified_at) - datetime.datetime.now()
    ).seconds < settings.SECONDS_BETWEEN_ADMIN_NOTIFICATIONS:
        log.warning('Admin wasn\'t notifiend, because was already notified at %s', admin_notified_at)
        return

    async with aiohttp.ClientSession(headers={
            'accept': 'application/json',
            'content-type': 'application/json',
            }) as session:
        async with session.post(
            settings.DISCORD_WEBHOOK,
            json={
                'username': f'{settings.BOT_NAME}_{settings.BOT_VERSION}',
                'content': f'```diff\n-{message}\n```',
            },
        ) as res:
            if res.status != 204:
                log.warning('Failed to send webhook, %s: %s', res.status, res)

            await redis_connector.save_data(
                key='admin_notified_at',
                data=time.mktime((datetime.datetime.now()).timetuple())
            )
