import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client, errors
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaAudio

import exceptions
import settings
from addons.Telemetry import (
    send_telemetry,
    MeasurementLabelTypeValue,
    TelemetryEventName,
    TelemetryMeasurement,
    TelemetryMeasurementLabels, )
from common.models import ThirdPartyAPIMediaType
from db.connector import database_connector
from helpers.base import api_adapter_module, BaseHelper
from helpers.state import redis_connector
from helpers.utils import get_monitoring_handler
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
        await message.reply(module.unhandled_error_text)
        raise  # unhanled error, let top-level decorator to know about it
    except exceptions.WrongInputException:
        await message.reply(text=module.wrong_input_text, reply_to_message_id=message.id)
    else:
        # collect all media links
        media_content = []
        for media in helper_data.items:
            match media.media_type:
                case ThirdPartyAPIMediaType.photo:
                    media_content.append(InputMediaPhoto(media=media.media_url))
                case ThirdPartyAPIMediaType.video:
                    media_content.append(InputMediaVideo(media=media.media_url))
                case ThirdPartyAPIMediaType.audio:
                    media_content.append(InputMediaAudio(media=media.media_url))
        # send media
        # add counter to keep media count in case of exceptions occur
        sent_counter = 0
        try:
            # split to n-sized chunks
            for media_groups in chunks(media_content, 10):
                await message.reply_media_group(media=media_groups)
                sent_counter += 10
            # reply with result text
            await message.reply_text(text=module.result_text)
        except errors.exceptions.bad_request_400.MediaEmpty:
            # if media contain unsupported video type for reply_media_group method
            for i in range(sent_counter, len(helper_data.items)):
                match helper_data.items[i].media_type:
                    case 1:
                        await message.reply_photo(
                            photo=helper_data.items[i].media_url,
                            reply_to_message_id=message.id if i == (len(helper_data.items) - 1) else None,
                            reply_markup=module.keyboard if hasattr(module, 'keyboard') else None,
                            caption=module.result_text if i == (len(helper_data.items) - 1) else None
                        )
                    case 2:
                        await message.reply_video(
                            video=helper_data.items[i].media_url,
                            reply_to_message_id=message.id if i == (len(helper_data.items) - 1) else None,
                            reply_markup=module.keyboard if hasattr(module, 'keyboard') else None,
                            caption=module.result_text if i == (len(helper_data.items) - 1) else None
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
        await message.reply(module.unhandled_error_text)
        raise  # unhanled error, let top-level decorator to know about it
    except exceptions.WrongInputException:
        await message.reply(text=module.wrong_input_text, reply_to_message_id=message.id)
    else:
        for media in helper_data.items:
            if media.media_type == ThirdPartyAPIMediaType.video:
                text = module.result_text.format(media_type='видео')
                await message.reply_video(
                    video=media.media_url,
                    reply_to_message_id=message.id,
                    reply_markup=module.keyboard,
                    caption=text
                )
            elif media.media_type == ThirdPartyAPIMediaType.audio:
                text = module.result_text.format(media_type='музыку')
                await message.reply_audio(
                    audio=media.media_url,
                    reply_to_message_id=message.id,
                    reply_markup=module.keyboard,
                    caption=text
                )


async def start_monitoring(
        client: Client,
        message: Message,
        module: BotModule,
        social_network: str,
        nickname: str,
        media_type: str,
) -> None:
    custom_error_message: str = getattr(module, 'error_text', api_adapter_module.unhandled_error_text)
    try:
        # get last item
        data = await get_monitoring_handler(module=module, social_network=social_network, media_type=media_type)(nickname, limit=1)
        data = data.items[0]

        # compare last item from storage
        last_data_id = await redis_connector.get_user_data(
            key='last_updated_item',
            user_id=message.from_user.id,
        )

        if last_data_id != data.media_id and last_data_id is not None:
            match data.media_type:
                case ThirdPartyAPIMediaType.photo:
                    await message.reply_photo(
                        caption=module.result_text.format(media_type=media_type, nickname=nickname),
                        photo=data.media_url,
                    )
                case ThirdPartyAPIMediaType.video:
                    await message.reply_video(
                        caption=module.result_text.format(media_type=media_type, nickname=nickname),
                        video=data.media_url,
                    )
                case ThirdPartyAPIMediaType.audio:
                    await message.reply_audio(
                        caption=module.result_text.format(media_type=media_type, nickname=nickname),
                        audio=data.media_url,
                    )

        # save last item id to storage
        await redis_connector.save_user_data(
            key='last_updated_item',
            data=data.media_id,
            user_id=message.from_user.id,
        )

    except exceptions.AccountIsPrivate:
        await message.reply(text=api_adapter_module.error_text_account_private, reply_to_message_id=message.id)
    except exceptions.AccountNotExist:
        await message.reply(text=api_adapter_module.error_text_account_not_found, reply_to_message_id=message.id)
    except exceptions.EmptyResultsException:
        await message.reply(text=custom_error_message, reply_to_message_id=message.id)
    except exceptions.ThirdPartyApiException:
        await message.reply(module.unhandled_error_text)
        raise  # unhanled error, let top-level decorator to know about it
    except exceptions.WrongInputException:
        await message.reply(text=module.wrong_input_text, reply_to_message_id=message.id)