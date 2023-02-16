import datetime
from dataclasses import dataclass

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    Message,
)

import settings
from addons.Trottling import handle_trottling_decorator
from common.decorators import (
    inform_user_decorator, handle_common_exceptions_decorator,
)
from common.filters import conversation_filter
from helpers.utils import get_helper_class_from_link
from jobs import scheduler, get_user_instagram_media
from models import BotModule
from plugins.base import callback as base_callback, get_modules_buttons


@dataclass
class InstagramModule(BotModule):
    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        buttons = get_modules_buttons()
        extra_buttons = []

        # align buttons in two columns
        bottom_menu_keys_iterator = iter(buttons)

        buttons_in_columns = list(
            zip(bottom_menu_keys_iterator, bottom_menu_keys_iterator)
        )

        # if number of buttons is odd, add missing one
        if len(buttons) % 2 != 0:
            extra_buttons.append(buttons[-1])

        """
        Buttons for ReplyKeyboardMarkup shoul be in form of:
        [ (button1, button2), (button3, button4), ... ]
        """
        buttons_in_columns.append(extra_buttons)

        return ReplyKeyboardMarkup(
            list(buttons_in_columns),
            one_time_keyboard=False,
            placeholder=self.friendly_name,
            resize_keyboard=True,
        )


module = InstagramModule('instagram')


@Client.on_message(filters.regex(rf'^{module.button}$') | filters.command(module.command))
@handle_trottling_decorator
@handle_common_exceptions_decorator
@inform_user_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)


@Client.on_message(filters.text & conversation_filter(module.name))
@handle_trottling_decorator
@handle_common_exceptions_decorator
@inform_user_decorator
async def handle_instagram_request(client: Client, message: Message) -> None:
    start_time = datetime.datetime.now()

    if current_jobs := scheduler.get_jobs():
        channel_stats_jobs = list(filter(lambda j: j.id.startswith('instagram-media'), current_jobs))
        if channel_stats_jobs:
            last_job = channel_stats_jobs[-1]
            start_time = last_job.next_run_time

    start_time += datetime.timedelta(seconds=settings.PENDING_DELAY)

    scheduler.add_job(
        get_user_instagram_media,
        id=f'instagram-media-{message.id}',
        trigger='date',
        name=f'Instagram media for {message.text}',
        max_instances=5,  # settings.ANNOUNCE_WORKERS,
        misfire_grace_time=None,  # run job even if it's time is overdue
        kwargs={
            'client': client,
            'module': module,
            'message': message,
            'helper_class': get_helper_class_from_link(message.text),
        },
        run_date=start_time,
    )

    await message.reply(module.pending_text)
