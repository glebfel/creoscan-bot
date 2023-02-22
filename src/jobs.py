import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client, errors
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo

import exceptions
import settings
from addons.Telemetry import (
    send_telemetry,
    MeasurementLabelTypeValue,
    TelemetryEventName,
    TelemetryMeasurement,
    TelemetryMeasurementLabels, )
from db.connector import database_connector
from helpers.base import api_adapter_module, BaseHelper
from models import BotModule
from utils import chunks

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
        helper_data = await helper_class(message).search_results
    except exceptions.AccountIsPrivate:
        await message.reply(text=api_adapter_module.error_text_account_private, reply_to_message_id=message.id)
    except exceptions.AccountNotExist:
        await message.reply(text=api_adapter_module.error_text_account_not_found, reply_to_message_id=message.id)
    except exceptions.EmptyResultsException:
        await message.reply(text=custom_error_message, reply_to_message_id=message.id)
    except exceptions.ThirdPartyApiException:
        await message.reply(api_adapter_module.unhandled_error_text)
        raise  # unhanled error, let top-level decorator to know about it
    except exceptions.WrongInputException:
        await message.reply(text=api_adapter_module.wrong_input_text, reply_to_message_id=message.id)
    else:
        # collect all media links
        media_content = []
        for media in helper_data:
            match media['media_type']:
                case 1:
                    media_content.append(InputMediaPhoto(media=media['image_versions2']['candidates'][0]['url']))
                case 2:
                    media_content.append(InputMediaVideo(media=media['video_versions'][0]['url']))

        try:
            # split to n-sized chunks
            for media_groups in chunks(media_content, 10):
                await message.reply_media_group(media=media_groups)
            # reply with result text
            await message.reply_text(text=module.result_text)
        except errors.exceptions.bad_request_400.MediaEmpty:
            # if media contain unsupported video type for reply_media_group method
            for ind, media in enumerate(helper_data):
                match media['media_type']:
                    case 1:
                        await message.reply_photo(
                            photo=media['image_versions2']['candidates'][0]['url'],
                            reply_to_message_id=message.id if ind == (len(helper_data) - 1) else None,
                            reply_markup=module.keyboard if hasattr(module, 'keyboard') else None,
                            caption=module.result_text if ind == (len(helper_data) - 1) else None
                        )
                    case 2:
                        await message.reply_video(
                            video=media['video_versions'][0]['url'],
                            reply_to_message_id=message.id if ind == (len(helper_data) - 1) else None,
                            reply_markup=module.keyboard if hasattr(module, 'keyboard') else None,
                            caption=module.result_text if ind == (len(helper_data) - 1) else None
                        )


async def get_tiktok_media(
        client: Client,
        helper_class: BaseHelper,
        message: Message,
        module: BotModule,
) -> None:
    custom_error_message: str = getattr(module, 'error_text', api_adapter_module.unhandled_error_text)

    try:
        helper_data = await helper_class(message).search_results
    except exceptions.AccountIsPrivate:
        await message.reply(text=api_adapter_module.error_text_account_private, reply_to_message_id=message.id)
    except exceptions.AccountNotExist:
        await message.reply(text=api_adapter_module.error_text_account_not_found, reply_to_message_id=message.id)
    except exceptions.EmptyResultsException:
        await message.reply(text=custom_error_message, reply_to_message_id=message.id)
    except exceptions.ThirdPartyApiException:
        await message.reply(api_adapter_module.unhandled_error_text)
        raise  # unhanled error, let top-level decorator to know about it
    except exceptions.WrongInputException:
        await message.reply(text=api_adapter_module.wrong_input_text, reply_to_message_id=message.id)
    else:
        if 'video' in helper_data['data']['play']:
            text = module.result_text.format(media_type='видео')
            await message.reply_video(
                video=helper_data['data']['play'],
                reply_to_message_id=message.id,
                reply_markup=module.keyboard,
                caption=text
            )
        else:
            text = module.result_text.format(media_type='музыку')
            await message.reply_audio(
                audio=helper_data['data']['play'],
                reply_to_message_id=message.id,
                reply_markup=module.keyboard,
                caption=text
            )