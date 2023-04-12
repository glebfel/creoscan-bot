import datetime
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
        # get last item
        data = await get_monitoring_media_handler_func(module=module, social_network=social_network,
                                                       media_type=media_type)(
            nickname, limit=1)
        data = data.items[0]

        # compare last item from storage
        last_data_id = await UserMonitoringRequestsDBConnector.get_last_updated_data_id(message.from_user.id)

        if (last_data_id != data.media_id and last_data_id is not None) or (last_data_id is None and data.taken_at >= datetime.datetime.now()):
            result_message = module.result_text.format(media_type=media_type, nickname=nickname)
            await message_handler(chat_id=message.chat.id, message=result_message, media=data)

        # save last item id to storage
        await UserMonitoringRequestsDBConnector.save_last_updated_data_id(data.media_id, message.from_user.id)

    except exceptions.AccountIsPrivate:
        await message_handler(chat_id=message.chat.id, message=api_adapter_module.error_text_account_private)
    except exceptions.AccountNotExist:
        await message_handler(chat_id=message.chat.id, message=api_adapter_module.error_text_account_not_found)
        monitoring_scheduler.remove_job(job_id=f'monitoring-{message.from_user.id}-{social_network}-{nickname}')
    except exceptions.EmptyResultsException:
        await message_handler(chat_id=message.chat.id, message=custom_error_message)
    except exceptions.ThirdPartyApiException:
        await message_handler(chat_id=message.chat.id, message=module.unhandled_error_text)
        raise