import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram.types import (
    Message,
)

import exceptions
import settings
from helpers.base import api_adapter_module
from models import BotModule
from plugins.Monitoring.utils import get_monitoring_media_handler_func, UserMonitoringRequestsDBConnector

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
        # get last media from api source
        new_data = await get_monitoring_media_handler_func(module=module, social_network=social_network,
                                                           media_type=media_type)(
            nickname, limit=1)
        if not new_data.items:
            return
        else:
            new_data = new_data.items[0]
        # compare last monitoring data from storage
        last_monitoring_data = await UserMonitoringRequestsDBConnector.get_last_updated_monitoring_data(message.chat.id)
        if (last_monitoring_data.data and
            last_monitoring_data.data.media_id != new_data.media_id and
            last_monitoring_data.data.taken_at < new_data.taken_at) or \
                (last_monitoring_data.data is None
                 and last_monitoring_data.last_updated_at < new_data.taken_at):
            result_message = module.result_text.format(media_type=media_type, nickname=nickname)
            await message_handler(chat_id=message.chat.id, message=result_message, media=new_data)
        # save last item id to storage
        await UserMonitoringRequestsDBConnector.save_last_updated_monitoring_data(data=new_data, user_id=message.chat.id)

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