import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram.types import (
    Message,
)

import exceptions
import settings
from helpers.base import api_adapter_module
from models import BotModule
from plugins.Monitoring.utils import get_monitoring_media_handler_func, UserMonitoringDataDBConnector

log = logging.getLogger(__name__)

monitoring_scheduler = AsyncIOScheduler()
monitoring_scheduler.add_jobstore(
    'redis',
    jobs_key='apscheduler.jobs',
    run_times_key='apscheduler.run_times',
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
)
monitoring_scheduler.start()


async def start_monitoring(
        message_handler: callable,
        message: Message,
        module: BotModule,
        social_network: str,
        nickname: str,
        media_type: str,
) -> None:
    custom_error_message: str = getattr(module, 'error_text', api_adapter_module.unhandled_error_text)
    try:
        # get job start time
        monitoring_start_date = (
            await UserMonitoringDataDBConnector.get_last_user_monitoring(user_id=message.chat.id)).start_date
        # get last monitoring media date from storage
        last_monitoring_media_date = await UserMonitoringDataDBConnector.get_last_monitoring_media_date(
            message.chat.id)
        # get last media from api source
        new_data = await get_monitoring_media_handler_func(module=module, social_network=social_network,
                                                           media_type=media_type)(nickname,
                                                                                  start_from=last_monitoring_media_date
                                                                                  if last_monitoring_media_date else monitoring_start_date)
        if new_data.items:
            result_message = module.result_text.format(media_type=media_type, nickname=nickname)
            await message_handler(chat_id=message.chat.id, message=result_message, media=new_data)
            # save last monitoring media date to storage
            await UserMonitoringDataDBConnector.save_last_monitoring_media_data(
                date=new_data.items[-1].taken_at,
                user_id=message.chat.id)
    except exceptions.AccountIsPrivate:
        await message_handler(chat_id=message.chat.id, message=api_adapter_module.error_text_account_private)
    except exceptions.AccountNotExist:
        await message_handler(chat_id=message.chat.id, message=api_adapter_module.error_text_account_not_found)
        monitoring_scheduler.remove_job(job_id=f'monitoring-{message.chat.id}-{social_network}-{nickname}')
    except exceptions.EmptyResultsException:
        await message_handler(chat_id=message.chat.id, message=custom_error_message)
    except exceptions.ThirdPartyApiException:
        await message_handler(chat_id=message.chat.id, message=module.unhandled_error_text)
        raise
