import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram.types import (
    Message,
)

import exceptions
import settings
from common.models import ThirdPartyAPIMediaType
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

        if last_data_id != data.media_id and last_data_id is not None:
            match data.media_type:
                case ThirdPartyAPIMediaType.photo:
                    await message.reply_photo(
                        caption=module.result_text.format(media_type=media_type, nickname=nickname),
                        photo=data.media_url,
                        reply_markup=module.result_keyboard,
                    )
                case ThirdPartyAPIMediaType.video:
                    await message.reply_video(
                        caption=module.result_text.format(media_type=media_type, nickname=nickname),
                        video=data.media_url,
                        reply_markup=module.result_keyboard,
                    )

        # save last item id to storage
        await UserMonitoringRequestsDBConnector.save_last_updated_data_id(data.media_id, message.from_user.id)

    except exceptions.AccountIsPrivate:
        await message.reply(text=api_adapter_module.error_text_account_private, reply_to_message_id=message.id)
    except exceptions.AccountNotExist:
        await message.reply(text=api_adapter_module.error_text_account_not_found, reply_to_message_id=message.id)
        monitoring_scheduler.remove_job(job_id=f'monitoring-{message.from_user.id}-{social_network}-{nickname}')
    except exceptions.EmptyResultsException:
        await message.reply(text=custom_error_message, reply_to_message_id=message.id)
    except exceptions.ThirdPartyApiException:
        await message.reply(module.unhandled_error_text)
        raise  # unhanled error, let top-level decorator to know about it
