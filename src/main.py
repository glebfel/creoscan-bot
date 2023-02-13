import datetime
import logging
from rich.logging import RichHandler
from typing import Optional

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import (
    CallbackQuery,
    Message,
)

import settings
from jobs import send_user_stats, scheduler
#-------------------


def main() -> None:

    # set up logging
    logging.basicConfig(level=settings.LOG_LEVEL,
                        format='%(name)s - %(message)s',
                        handlers=[RichHandler(rich_tracebacks=True)])
    # disable annoying logs
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('asyncio_redis').setLevel(logging.WARNING)
    logging.getLogger('pyrogram').setLevel(logging.WARNING)

    plugins = dict(
        root='plugins',
        include=settings.PLUGINS,
    )

    bot = Client(
        settings.BOT_NAME,
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        bot_token=settings.BOT_TOKEN,
        plugins=plugins,
    )

    # send stats
    start_time: datetime.datetime = datetime.datetime.now() + datetime.timedelta(seconds=30)
    scheduler.add_job(
        send_user_stats,
        id='user_stats_telemetry',
        trigger='interval',
        next_run_time=start_time,
        name='User stats telemetry',
        seconds=settings.SEND_USER_STATS_INTERVAL_S,  # trigger argument
    )

    # starting the bot
    logging.getLogger(__name__).info(
        'Starting Bot [bold yellow]%s [/]([blue]%s[/])...',
        settings.BOT_NAME,
        settings.BOT_VERSION,
        extra={'markup': True})

    bot.run()


if __name__ == '__main__':
    main()
