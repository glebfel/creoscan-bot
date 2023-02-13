import datetime
import logging
from dataclasses import dataclass, field, fields

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)

import settings
from addons.Telemetry import SendUserActionEventDecorator
from addons.Trottling import (
    handle_paid_requests_trottling_decorator,
    handle_trottling_decorator,
)
from common.decorators import (
    handle_common_exceptions_decorator,
    inform_user_decorator,
)
from common.filters import conversation_filter
from jobs import get_channel_stats, scheduler
from helpers.TgStatParser import TgChannelParserHelper
from models import BotModule

from ..base import callback as base_callback


log = logging.getLogger(__name__)


@dataclass
class TgStatModule(BotModule):
    error_text: str = field(init=False)
    pending_text: str = field(init=False)
    result_text: str = field(init=False)
    button_contact: str = field(init=False)
    url_contact: str = field(init=False)

    @property
    def share_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(self.button_contact, url=self.url_contact)]
        ])


module = TgStatModule(name='channel_stats')


# TODO make button & command as additional filter
@Client.on_message(filters.regex(rf'^{module.button}$') | filters.command(module.command))
@handle_common_exceptions_decorator
@handle_trottling_decorator
@inform_user_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)


@Client.on_message(filters.text & conversation_filter(module.name))
@handle_common_exceptions_decorator
@handle_paid_requests_trottling_decorator
@handle_trottling_decorator
@inform_user_decorator
async def handle_stats(client: Client, message: Message) -> None:
    start_time = datetime.datetime.now()

    if (current_jobs := scheduler.get_jobs()):
        channel_stats_jobs = list(filter(lambda j: j.id.startswith('channel_stats'), current_jobs))
        if channel_stats_jobs:
            last_job = channel_stats_jobs[-1]
            start_time = last_job.next_run_time

    start_time += datetime.timedelta(seconds=settings.PENDING_DELAY)

    scheduler.add_job(
        get_channel_stats,
        id=f'channel_stats-{message.id}',
        trigger='date',
        name=f'ChannelSats job for channel {message.text}',
        max_instances=5,  #settings.ANNOUNCE_WORKERS,
        misfire_grace_time=None,  # run job even if it's time is overdue
        kwargs={
            'client': client,
            'module': module,
            'message': message,
            'helper_class': TgChannelParserHelper,
        },
        run_date=start_time,
    )

    await message.reply(module.pending_text)
