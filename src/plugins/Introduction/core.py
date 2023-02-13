from dataclasses import dataclass, field
import importlib
import logging
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

import settings
from addons.Trottling import (
    handle_paid_requests_trottling_decorator,
    handle_trottling_decorator,
)
from addons.Telemetry import (
    send_telemetry,
    MeasurementLabelTypeValue,
    TelemetryEvent,
    TelemetryEventName,
    TelemetryMeasurement,
    TelemetryMeasurementLabels,
    EventLabelResultStatusValue,
    EventLabelUserActionTypeValue,
    UserActionEventLabels,
    SendUserActionEventDecorator,
    EventLabelAccountActionTypeValue,
    AccountEventLabels,
)

from common.decorators import (
    handle_common_exceptions_decorator,
    inform_user_decorator,
)
from db.connector import database_connector
from models import BotModule

from ..base import callback as base_callback
from ..base import get_modules_buttons


log = logging.getLogger(__name__)


@dataclass
class IntroductionModule(BotModule):
    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        buttons = get_modules_buttons()
        extra_buttons = []

        # align buttons in two columns
        bottom_menu_keys_iterator = iter(buttons)

        buttons_in_columns = list(
            zip(bottom_menu_keys_iterator, bottom_menu_keys_iterator)
        )

        # if number of buttons is odd, add missing one
        if len(buttons) % 2 != 0:
            extra_buttons.append(buttons[-1])

        """
        Buttons for ReplyKeyboardMarkup shoul be in form of:
        [ (button1, button2), (button3, button4), ... ]
        """
        buttons_in_columns.append(extra_buttons)

        return ReplyKeyboardMarkup(
            list(buttons_in_columns),
            one_time_keyboard=False,
            placeholder=self.friendly_name,
            resize_keyboard=True,
        )


module = IntroductionModule(name='introduction')


@Client.on_message(filters.command('start'))
@handle_common_exceptions_decorator
@handle_trottling_decorator
@SendUserActionEventDecorator(in_module=module.name)
@inform_user_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    # Set new commands for bottom-left (blue) menu
    '''
    await client.set_bot_commands([
        BotCommand("start", "Перезапустить бота"),
        *[
            BotCommand(submodule.command, submodule.friendly_name)
            for submodule in self.submodules if submodule.command
        ]
    ])
    '''

    # save or update the user in DB
    userdata = dict(
        user_id=update.from_user.id,
        firstname=update.from_user.first_name,
        lastname=update.from_user.last_name,
        username=update.from_user.username,
        chat_id=update.from_user.id,
    )

    user = await database_connector.get_user(
        username=update.from_user.username,
        user_id=update.from_user.id,
    )
    log.debug('User exists: %s', user)

    utm = [str(arg) for arg in update.command if str(arg).startswith('utm_')]
    log.debug('Got utm list: %s', utm)

    if utm and (
        not user  # new user
        or not user.utm_created_at  # old user, but never followed utm
        or user.utm_created_at + timedelta(days=settings.UTM_COOLDOWN_DAYS) < datetime.now()  # utm is outdated
    ):
        userdata['utm'] = utm

    if not user or user.blocked:
        _event_type = EventLabelAccountActionTypeValue.registration if not user\
                      else EventLabelAccountActionTypeValue.unblock

        # send registration event
        log.debug('Sending %s event...', 'registration' if not user else 'unblocking')
        await send_telemetry(
            TelemetryEvent(
                event_name=TelemetryEventName.tgbot_account_event,
                event_labels=AccountEventLabels(
                        event_type=_event_type,
                        registration_source=' '.join(utm) if utm else 'self',
                        status=EventLabelResultStatusValue.success,
                )))

    log.debug('Saving user: %s', userdata)
    await database_connector.store_or_update_user(**userdata)

    await base_callback(client, module, update)
