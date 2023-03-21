import asyncio
import logging
# import re

from pyrogram import Client, errors
from pyrogram.enums import ParseMode
from pyrogram.types import Message

import settings  # type: ignore
from db.connector import database_connector  # type: ignore
from common.decorators import handle_common_exceptions_decorator  # type: ignore
from common.models import AnnounceJobStats, AnnouncePreferences  # type: ignore
from exceptions import UnrecognizedException  # type: ignore
from helpers.notify import notify_admin  # type: ignore
from helpers.state import redis_connector  # type: ignore
from jobs import scheduler  # type: ignore


log = logging.getLogger(__name__)


async def announce_to_all_users(
    announce_message: Message,
    client: Client,
    ids: list,
    job_id: str,
    job_stats: AnnounceJobStats,
    announce_preferences: AnnouncePreferences,
) -> None:
    """
    This job supposed to be run in defined interval.
    On each iteration some amount of users is picked up from ids list,
    the amount is dynamic: in case of flood it is reduced.

    There are two pauses:
    - between job runs, defined by ANNOUNCE_INTERVAL_S
    - between each user announce, defined by `1/announce_preferences.pack_length`
    """

    # TODO multiply pack_length on seconds between job runs
    for i in range(0, announce_preferences.pack_length):
        if not ids:
            log.debug('No users left, removing job...')
            if _scheduled_job := scheduler.get_job(job_id):
                _scheduled_job.remove()
            return

        user_id = ids.pop()
        log.debug('Poped next user: %s', user_id)

        if not user_id:
            return

        # anti-flood delay
        await asyncio.sleep(1/announce_preferences.pack_length)

        try:
            # send message to user
            await _announce_user_with_error_handling_and_stats_count(
                client=client,
                job_stats=job_stats,
                message=announce_message,
                preferences=announce_preferences,
                user_id=user_id,
            )
        except UnrecognizedException as exc:
            # continue job, ignore exceptions
            log.exception('Unhandled exception occured during announcement: %s', exc)


@handle_common_exceptions_decorator
async def _announce_user_with_error_handling_and_stats_count(
        user_id: int, client: Client,
        job_stats: AnnounceJobStats, preferences: AnnouncePreferences, message: Message) -> None:
    try:
        await _announce_user(client=client, user_id=user_id, preferences=preferences, message=message)
        await database_connector.user_was_announced(user_id)
        job_stats.success += 1
    except (
        errors.InputUserDeactivated,
        errors.PeerIdInvalid,
        errors.UserIsBlocked,
        errors.UserIsBot,
    ) as exc:
        log.debug('Error happened for user %s: %s', user_id, exc)
        await database_connector.user_toggle_block(user_id)
        job_stats.blocked += 1
    except errors.FloodWait as exc:
        log.debug('Flood error: %s', exc)
        # decrease pack per interval to avoid flood
        preferences.pack_length = 1
        raise exc  # pass exception to global handler
    except Exception as exc:
        log.debug('Unknown error: %s', exc)
        job_stats.failed += 1
        await notify_admin(f'Необработанная ошибка рассылки: {exc}')
        raise exc  # pass exception to global handler
    else:
        # bring back default interval between announcements
        preferences.pack_length = settings.ANNOUNCE_PACK_LENGTH


async def _announce_user(user_id: int, client: Client,
                         preferences: AnnouncePreferences, message: Message) -> None:
    """
    Poll object must be preserved to allow users see votes of others.
    However, `copy_message` creates new instance of Poll.
    Possible solution is to use `sendMedia` from raw Telegram Bot API.
    """
    if hasattr(message, 'poll') and message.poll:
        await message.forward(
            chat_id=user_id,  # announce to tet-a-tet user chat
            disable_notification=not preferences.notification,
        )
    elif hasattr(message, 'media') and message.media:
        await message.copy(
            chat_id=user_id,  # announce to tet-a-tet user chat
            disable_notification=not preferences.notification,
            parse_mode=ParseMode.MARKDOWN if preferences.markdown else ParseMode.DISABLED,
            reply_markup=None,
        )
    else:
        # re-create message for proper params preserving,
        # message.copy() does not preserve .web_page
        await client.send_message(
            chat_id=user_id,
            text=message.text.markdown,
            disable_notification=not preferences.notification,
            disable_web_page_preview=not preferences.link_preview,
            parse_mode=ParseMode.MARKDOWN if preferences.markdown else ParseMode.DISABLED,
            reply_markup=None,
        )


@handle_common_exceptions_decorator
async def announce_status_feedback(job_id: str, job_stats: AnnounceJobStats,
                                   stats_message: Message) -> None:
    """
    Report back to admin chat about announcement progress.
    """
    _status_text = await _get_status_message_text(job_stats)

    # TODO time
    '''
    from zoneinfo import ZoneInfo

    nyc = ZoneInfo("America/New_York")
    localized = datetime(2022, 6, 4, tzinfo=nyc)
    print(f"Datetime: {localized}, Timezone: {localized.tzname()}, TZ Info: {localized.tzinfo}")
    # Datetime: 2022-06-04 00:00:00-04:00, Timezone: EDT, TZ Info: America/New_York
    '''

    if not scheduler.get_job(job_id):
        await stats_message.edit_text(f'**Рассылка завершилась**{_status_text}')

        # remove self from scheduler
        scheduler.remove_job(f'{job_id}-feedback')
        await redis_connector.delete_data(f'{job_id}-preferences')
        return

    await stats_message.edit_text((
            f'Рассылка идет{_status_text}'
            f'\n\nETA: ~**{job_stats.eta.strftime("%H:%M:%S")}**'
        ),
        reply_markup=stats_message.reply_markup,
        parse_mode=ParseMode.MARKDOWN)


async def _get_status_message_text(stats: AnnounceJobStats) -> str:
    return (
        '\n\n'
        f'Всего: **{stats.sent}** из **{stats.total}**\n'
        f'  успешно: **{stats.success}**\n'
        f'  бот заблокирован: **{stats.blocked}**\n'
        f'  другие ошибки: **{stats.failed}**\n\n'
        f'Время старта: **{stats.started_at}**\n'
        f'Прошло минут: ~{stats.spent_time_m}\n'
        f'Скорость рассылки: ~{stats.rate} сообщений/мин'
    )
