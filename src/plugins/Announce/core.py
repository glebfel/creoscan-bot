import datetime
import logging
from dataclasses import dataclass

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import settings  # type: ignore
from addons.Permissions import restricted_method_decorator  # type: ignore
from addons.Trottling import handle_trottling_decorator  # type: ignore
from db.connector import database_connector  # type: ignore
from common.filters import conversation_filter  # type: ignore
from common.decorators import handle_common_exceptions_decorator  # type: ignore
from common.models import (  # type: ignore
    AnnouncePreferences,
    AnnounceJobStats,
    UserRoleBit,
)
from helpers.state import redis_connector  # type: ignore
from models import BotModule  # type: ignore
from jobs import scheduler  # type: ignore

from ..base import callback as base_callback  # type: ignore
from .jobs import announce_to_all_users, announce_status_feedback  # type: ignore
from .utils import copy_message_with_preferences  # type: ignore


log = logging.getLogger(__name__)


@dataclass
class AnnounceModule(BotModule):
    allowed_role = UserRoleBit.admin
    friendly_name = 'Массовая рассылка'
    command = ''
    icon = ''
    description = 'DESC ANN'

    header_text = 'hhh'
    footer_text = 'fff'
    pending_text = 'ppp'
    result_text = 'rrr'

    current_module_text = 'Вы находитесь в модуле {}.'
    help_command_text = 'HELP ADMIN TEXT'
    unknown_command_text = 'UNKNOWN ADMIN TEXT'
    unhandled_error_text = 'UNHA ADMIN TEXT'
    wrong_input_text = 'WRONG INP ADMIN TEXT'
    introduction_text = ((
                'Пришли сообщение для массовой рассылки.\n\n'
                '__перед началом рассылки ты увидишь предпоказ итогового сообщения__'))


module = AnnounceModule('admin_announce')


@Client.on_message(filters.regex(rf'^{module.button}$'))
@handle_common_exceptions_decorator
@handle_trottling_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)


@Client.on_message(conversation_filter(module.name))
@handle_common_exceptions_decorator
@handle_trottling_decorator
@restricted_method_decorator
async def handle_message(client: Client, message: Message, helper_data: dict = {}) -> None:
    """
    Set defaults.
    Hint:
        - default Tg message parse mode is HTML.
        - default Tg link preview is on.
    """
    preferences = AnnouncePreferences()

    announce_message = await copy_message_with_preferences(
        source_message=message,
        preferences=preferences,
        reply_markup=await _get_settings_keyboard(
            message=message,
            link_preview=preferences.link_preview,
            markdown=preferences.markdown,
            notification=preferences.notification,
        ))

    # save preferences for the announcement for future edition
    await redis_connector.save_data(
        key=await _get_job_preferences_key(announce_message.id),
        data=preferences)

    await announce_message.reply((
            'Это сообщение будет разослано **всем** пользователям.\n\n'
            '**Внимательно проверь, что текст и медиафайл (если есть) корректны!**\n'
            'Если что-то неверно, пришли сообщение заново.\n\n'
            '__сообщение выглядит так, как оно будет отправлено пользователю, '
            'настройки можно изменить кнопками под сообщением__'
        ),
        reply_to_message_id=announce_message.id,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('Начать рассылку', callback_data='ANNOUNCE_START')],
        ]))


@Client.on_callback_query(filters.regex('^ANNOUNCE_EDIT') & conversation_filter(module.name))
@handle_common_exceptions_decorator
@handle_trottling_decorator
@restricted_method_decorator
async def handle_edit_settings(client: Client, callback_query: CallbackQuery) -> None:
    _, _, changed_setting = callback_query.data.split('_')

    job_preferences_key = await _get_job_preferences_key(callback_query.message.id)
    preferences: AnnouncePreferences = AnnouncePreferences(**await redis_connector.get_data(job_preferences_key))

    if changed_setting == 'MARKDOWN':
        preferences.markdown = not preferences.markdown

    if changed_setting == 'NOTIFICATION':
        preferences.notification = not preferences.notification

    if changed_setting == 'LINKPREVIEW':
        preferences.link_preview = not preferences.link_preview

    await redis_connector.save_data(
        key=job_preferences_key,
        data=preferences,
    )

    _common_params = dict(
        parse_mode=ParseMode.MARKDOWN if preferences.markdown else ParseMode.DISABLED,
        reply_markup=await _get_settings_keyboard(
            message=callback_query.message,
            link_preview=preferences.link_preview,
            markdown=preferences.markdown,
            notification=preferences.notification,
        ))
    if callback_query.message.caption:
        await callback_query.message.edit_caption(
            caption=callback_query.message.caption.markdown,
            **_common_params,
        )
    elif callback_query.message.text:
        await callback_query.message.edit_text(
            text=callback_query.message.text.markdown,
            disable_web_page_preview=not preferences.link_preview,
            **_common_params,
        )


@Client.on_callback_query(filters.regex('^ANNOUNCE_START') & conversation_filter(module.name))
@handle_common_exceptions_decorator
@handle_trottling_decorator
@restricted_method_decorator
async def handle_announce_start(client: Client, callback_query: CallbackQuery) -> None:
    announce_message = callback_query.message.reply_to_message

    # remove inline buttons
    if announce_message.reply_markup:
        await announce_message.edit_reply_markup()

    job_id = await _get_job_id(announce_message.id)
    job_preferences_key = await _get_job_preferences_key(announce_message.id)
    announce_preferences: AnnouncePreferences = AnnouncePreferences(
        **await redis_connector.get_data(job_preferences_key))

    start_time: datetime.datetime = datetime.datetime.now() + datetime.timedelta(seconds=settings.ANNOUNCE_DELAY_S)
    chat_ids = await database_connector.get_user_ids_for_announce()

    job_stats: AnnounceJobStats = AnnounceJobStats(
        started_at=datetime.datetime.now().strftime(settings.DATE_FORMAT),
        total=len(chat_ids))

    announce_stats_message = await callback_query.message.edit_text((
            f'Рассылка **{job_stats.total}** пользователям будет начата через '
            f'**{settings.ANNOUNCE_DELAY_S}** сек (в '
            f'**{start_time.strftime("%H:%M:%S")}**)'
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('Отменить рассылку', callback_data='ANNOUNCE_CANCEL')],
        ]))

    # schedule announcement
    scheduler.add_job(
        announce_to_all_users,
        'interval',
        id=job_id,
        next_run_time=start_time,
        name=f'Announcement job {job_id} to all users',
        max_instances=settings.ANNOUNCE_WORKERS,
        misfire_grace_time=None,  # run job even if it's time is overdue
        kwargs={
            'announce_message': announce_message,
            'announce_preferences': announce_preferences,
            'client': client,
            'ids': chat_ids,
            'job_id': job_id,
            'job_stats': job_stats,
        },
        seconds=settings.ANNOUNCE_INTERVAL_S,
    )

    # schedule job status notification update
    scheduler.add_job(
        announce_status_feedback,
        'interval',
        id=f'{job_id}-feedback',
        next_run_time=start_time,
        name=f'Announcement job {job_id} feedback',
        kwargs={
            'job_id': job_id,
            'job_stats': job_stats,
            'stats_message': announce_stats_message,
        },
        seconds=settings.ANNOUNCE_FEEDBACK_INTERVAL_S,
    )


@Client.on_callback_query(filters.regex('^ANNOUNCE_CANCEL') & conversation_filter(module.name))
@handle_common_exceptions_decorator
@restricted_method_decorator
async def handle_announce_cancel(client: Client, callback_query: CallbackQuery) -> None:
    job_id = await _get_job_id(callback_query.message.reply_to_message.id)
    log.warning('Aborting announcement %s...', job_id)

    # stop announcement job, feedback job will be stopped by itself
    if _scheduled_job := scheduler.get_job(job_id):
        _scheduled_job.remove()
        await callback_query.message.edit_text(f'**Рассылка отстанавливается...**\n\n{callback_query.message.text}')
        log.warning('Announcement %s is manually aborted!', job_id)


async def _get_settings_keyboard(message: Message,
                                 markdown: bool, notification: bool, link_preview: bool) -> InlineKeyboardMarkup:
    buttons: list = [
        [InlineKeyboardButton(
            f'Звуковое уведомление: {await _humanize_bool(notification)}',
            callback_data='ANNOUNCE_EDIT_NOTIFICATION',
        )]]
    if message.caption or message.text:
        buttons.append(
            [InlineKeyboardButton(
                f'Markdown: {await _humanize_bool(markdown)}',
                callback_data='ANNOUNCE_EDIT_MARKDOWN',
            )])
    if message.text:
        buttons.append(
            [InlineKeyboardButton(
                f'Предпросмотр ссылок: {await _humanize_bool(link_preview)}',
                callback_data='ANNOUNCE_EDIT_LINKPREVIEW',
            )])
    return InlineKeyboardMarkup(buttons)


async def _humanize_bool(value: bool) -> str:
    return 'вкл' if value else 'выкл'


async def _get_job_id(message_id: int) -> str:
    return f'announce-{message_id}'


async def _get_job_preferences_key(message_id: int) -> str:
    return f'announce-{message_id}-preferences'
