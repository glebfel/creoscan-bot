import logging

from pyrogram import Client
from rich.logging import RichHandler

import settings


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

    # starting the bot
    logging.getLogger(__name__).info(
        'Starting Bot [bold yellow]%s [/]([blue]%s[/])...',
        settings.BOT_NAME,
        settings.BOT_VERSION,
        extra={'markup': True})

    bot.run()


if __name__ == '__main__':
    main()
