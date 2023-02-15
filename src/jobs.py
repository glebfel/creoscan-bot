import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client
from pyrogram.types import Message

import exceptions
import settings
from addons.Telemetry import (
    send_telemetry,
    MeasurementLabelTypeValue,
    TelemetryEventName,
    TelemetryMeasurement,
    TelemetryMeasurementLabels, ExternalAPIEventLabels, TelemetryEvent, EventLabelResultStatusValue,
)
from db.connector import database_connector
from helpers.base import api_adapter_module, BaseHelper
from helpers.utils import extract_username_from_link
from models import BotModule

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()
scheduler.start()


async def send_user_stats():
    """
    Send Measurement with total number of unblocked users
    """
    if not settings.SEND_PLATFORM_METRICS_DATA:
        log.debug('Skip sending user stats')
        return

    # TODO add scheduling and interval here

    user_count = await database_connector.get_users_count()
    log.info('Sending user stats: %s', user_count)

    await send_telemetry(
        TelemetryMeasurement(
            event_name=TelemetryEventName.tgbot_account_measurement,
            event_labels=TelemetryMeasurementLabels(measurement_type=MeasurementLabelTypeValue.total_registrations),
            value=user_count,
        ))


async def get_user_instagram_media(
        client: Client,
        helper_class: BaseHelper,
        message: Message,
        module: BotModule,
) -> None:
    custom_error_message: str = getattr(module, 'error_text', api_adapter_module.unhandled_error_text)

    try:
        result_status = EventLabelResultStatusValue.success
        helper_data = await helper_class(message).search_results
    except exceptions.AccountIsPrivate:
        result_status = EventLabelResultStatusValue.account_is_private
        await message.reply(text=api_adapter_module.error_text_account_private, reply_to_message_id=message.id)
    except exceptions.AccountNotExist:
        result_status = EventLabelResultStatusValue.account_not_exists
        await message.reply(text=api_adapter_module.error_text_account_not_found, reply_to_message_id=message.id)
    except exceptions.EmptyResultsException:
        result_status = EventLabelResultStatusValue.empty
        await message.reply(text=custom_error_message, reply_to_message_id=message.id)
    except exceptions.ThirdPartyApiException:
        result_status = EventLabelResultStatusValue.error
        await message.reply(api_adapter_module.unhandled_error_text)
        raise  # unhanled error, let top-level decorator to know about it
    except exceptions.WrongInputException:
        result_status = EventLabelResultStatusValue.wrong_input
        await message.reply(text=api_adapter_module.wrong_input_text, reply_to_message_id=message.id)
    else:
        text = module.result_text.format(
            account=extract_username_from_link(message.text),
        ).strip()

        match helper_data['media_type']:
            case 1:
                await message.reply_photo(
                    photo=helper_data['image_versions2']['candidates'][0]['url'],
                    reply_to_message_id=message.id,
                    reply_markup=module.keyboard if hasattr(module, 'keyboard') else None,
                    caption=text
                )
            case 2:
                await message.reply_video(
                    video=helper_data['video_versions'][0]['url'],
                    reply_to_message_id=message.id,
                    reply_markup=module.keyboard if hasattr(module, 'keyboard') else None,
                    caption=text
                )
    # finally:
    #     labels_kwargs = dict(
    #         provider='TgStat',
    #         status=result_status,
    #     )
    #     await send_telemetry(
    #         TelemetryEvent(
    #             event_labels=ExternalAPIEventLabels(**labels_kwargs),
    #             event_name=TelemetryEventName.tgbot_external_api_event,
    #         ))
