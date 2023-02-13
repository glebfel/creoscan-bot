import asyncio
import datetime
import logging
import re
import time
from random import randint

from pyrogram import errors
from pyrogram.types import Message

import settings
from common.models import MessagePreferences
from exceptions import UnrecognizedException
from helpers.notify import notify_admin
from helpers.state import redis_connector


log = logging.getLogger(__name__)


async def copy_message_with_preferences(source_message: Message, preferences: MessagePreferences,
                                        reply_markup: list) -> Message:
    """
    Bot can't edit user's messages, so a copy of source_message is edited instead.

    message.copy() doesn't preserve .web_page, or to be more specific, original
    message doesn't content .web_page for some reason.
    Seems like .web_page is deprecated.
    """
    _common_params = dict(
        parse_mode='Markdown' if preferences.markdown else None,
        reply_markup=reply_markup,
    )

    if source_message.media or source_message.poll:
        _common_params.update(dict(chat_id=source_message.from_user.id))
        if not source_message.poll:
            _common_params.update(dict(caption=source_message.caption.markdown))
        return await source_message.copy(**_common_params)
    else:
        _common_params.update(dict(
            disable_web_page_preview=not preferences.link_preview,
            text=source_message.text.markdown,
        ))
        return await source_message.reply(**_common_params)


async def perform_func_with_error_handling(func, *args, **kwargs):
    # perform method logic with error handling
    try:
        if await _wait_if_flood():
            # sleep a little bit more before resuming
            await asyncio.sleep(randint(1, settings.TELEGRAM_FLOOD_CONTROL_PAUSE_S))
        else:
            await _clear_global_flood_delay()
            await func(*args, **kwargs)
            # TODO resume jobs
    except (
        errors.InputUserDeactivated,
        errors.MessageNotModified,  # happens anywhere when edited text is equal source text
        errors.PeerIdInvalid,
        errors.QueryIdInvalid,  # too old query?
        errors.UserIsBlocked,
        errors.UserIsBot,
    ) as exc:
        log.debug('Skippable exception: %s', exc)
    except (
        # TODO inherit from one SkippableException
        exceptions.EmptyResultsException,
        exceptions.AccountIsPrivate,
        exceptions.AccountNotExist,
        exceptions.WrongInputException,
    ) as exc:
        log.debug('Exception %s meant to be handled above', exc)

    # usually it's wrong Markdown, probably handle this in announcement module
    # if re.match(r'Can\'t parse entities', exc.MESSAGE):
    #   log.exception('Failed to parse message: %s', exc.MESSAGE)
    except errors.FloodWait as exc:
        # Telegram says: [420 FLOOD_WAIT_X] - A wait of 37 seconds is required (caused by "messages.EditMessage")
        # TODO parse
        log.warning('Flood control: %s | %s | %s', exc.MESSAGE, exc.CODE, exc.NAME)
        log.warning('Flood control exc: %s -- %s', str(exc), dir(exc))
        # DEBUG
        try:
            log.warning('Flood control parsed: %s', re.findall('[0-9]+', str(exc))[-1:])
        except Exception:
            pass
        await _save_global_flood_delay(delay=settings.TELEGRAM_FLOOD_CONTROL_PAUSE_S)
        await _pause_announce()
        await notify_admin('Telegram flood warning')

    except Exception as exc:
        raise UnrecognizedException(exc)


async def _pause_announce() -> None:
    from jobs import scheduler
    running_jobs = scheduler.get_jobs()
    log.info('Jobs list: %s', running_jobs)


async def _save_global_flood_delay(delay_s: int) -> None:
    # save date in future until which we should wait before repeating request
    await redis_connector.save_data(
        key='flood_wait_until',
        data=time.mktime((
            datetime.datetime.now() + datetime.timedelta(seconds=delay_s)
        ).timetuple()))


async def _clear_global_flood_delay() -> None:
    await redis_connector.delete_data(key='flood_wait_until')


async def _wait_if_flood() -> bool:
    if not (flood_wait_until_s := await redis_connector.get_data(key='flood_wait_until')):
        return False

    flood_wait_until = datetime.datetime.fromtimestamp(flood_wait_until_s)

    if flood_wait_until > datetime.datetime.now():
        # flood_wait_for_s = (flood_wait_until - datetime.datetime.now()).seconds
        log.warning('Waiting for flood deadline: %s', flood_wait_until)
        return True
