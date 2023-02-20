import aiohttp
import enum
import logging
from dataclasses import asdict, dataclass, field, fields, InitVar
from typing import Optional, Tuple

from pyrogram.types import (
    CallbackQuery,
    Message,
)

import exceptions
import settings
from common.models import AutoNameEnum
from helpers.state import redis_connector
from utils import validate_type


log = logging.getLogger(__name__)


class TelemetryType(AutoNameEnum):
    event = enum.auto()
    measurement = enum.auto()


# possible values for some pre-defined event labels

class EventLabelAccountActionTypeValue(AutoNameEnum):
    block = enum.auto()
    registration = enum.auto()
    unblock = enum.auto()


class EventLabelCommonActionValue(AutoNameEnum):
    data_requested = enum.auto()
    download_csv = enum.auto()
    download_csv_with_rates = enum.auto()
    edit_hashtags_cloud = enum.auto()
    option_selected = enum.auto()
    wrong_command = enum.auto()


class EventLabelProviderValue(AutoNameEnum):
    # TODO move to ThirdPartyAdapter
    GoogleVision = enum.auto()
    Lamadava = enum.auto()
    RapidAPI = enum.auto()


class EventLabelResultStatusValue(AutoNameEnum):
    # TODO auto-generate from exceptions
    account_not_exists = enum.auto()
    account_is_private = enum.auto()
    error = enum.auto()
    empty = enum.auto()
    success = enum.auto()
    wrong_input = enum.auto()


class EventLabelUserActionTypeValue(AutoNameEnum):
    button_pressed = enum.auto()
    send_command = enum.auto()
    send_media = enum.auto()
    send_text = enum.auto()


class MeasurementLabelTypeValue(AutoNameEnum):
    total_registrations = enum.auto()


class TelemetryEventName(AutoNameEnum):
    """
    General Event names (aka types).
    Each of these supposed to be followed by uniq set of labels.
    """
    tgbot_account_event = enum.auto()
    tgbot_account_measurement = enum.auto()
    tgbot_external_api_event = enum.auto()
    tgbot_user_action_event = enum.auto()  # all user interactions: buttons, menus


@dataclass
class TelemetryLabels:
    def __post_init__(self):
        """
        After __init__ `event_type` value is an Enum instance.
        Loop over all fields and if field value is an enum, then set
        the field (i.e. attr) to the value of the enum.
        """
        for f in fields(self):
            if isinstance((value := getattr(self, f.name)), enum.Enum):
                setattr(self, f.name, value.value)
            if isinstance((value := getattr(self, f.name)), bool):
                setattr(self, f.name, str(value))


@dataclass
class TelemetryEventLabels(TelemetryLabels):
    """
    Event 'tags' to destinguish metrics with the same name by something.
    Here are the common ones, that will be attachad to any Event/Measurement.
    """
    status: EventLabelResultStatusValue   # is action successful or error occured


@dataclass
class TelemetryMeasurementLabels(TelemetryLabels):
    measurement_type: MeasurementLabelTypeValue


@dataclass
class AccountEventLabels(TelemetryEventLabels):
    event_type: EventLabelAccountActionTypeValue
    registration_source: Optional[str]  # e.g. utm compaign


@dataclass
class ExternalAPIEventLabels(TelemetryEventLabels):
    provider: EventLabelProviderValue


@dataclass
class UserActionEventLabels(TelemetryEventLabels):
    action_type: EventLabelUserActionTypeValue
    action_entity: str  # name of button, command text, media type
    in_module: str  # name of module that handled this event
    in_conversation: str  # name of saved conversation state, i.e. in which module user really is


# following entities are the ones which actually sent to dashboard

@dataclass
class TelemetryEvent:
    """
    Event entity, which is sent to dashboard.
    Each Event has a name (choose from TelemetryEventName) which describes "type" of event
    and labels (choose from TelemetryEventLabelName) which allows to destinguish events of
    similar type from each other by the lable (e.g. source of event, user id, etc).
    """

    # these fileds are assigned in __post_init__, where
    # validation of 'input' data from event_* fields is done
    name: str = field(init=False, default='')
    labels: Optional[dict] = field(init=False, default=None)

    event_name: InitVar[TelemetryEventName]
    event_labels: InitVar[TelemetryEventLabels]

    def __post_init__(self, event_name, event_labels):
        """
        After __init__ ensure that all assigned values are from allowed
        number of values (defined by AutoNameEnum).
        """
        validate_type(event_name, TelemetryEventName)
        self.name = event_name.value

        validate_type(event_labels, (TelemetryEventLabels, TelemetryMeasurementLabels))
        self.labels = {k: v for k, v in asdict(event_labels).items() if v}

    def __str__(self):
        return f'Event {self.name} {self.labels}'


@dataclass
class TelemetryMeasurement(TelemetryEvent):
    """
    Measurement entity, which is sent to dashboard.
    """
    value: int = 0

    def __str__(self):
        return f'Measurement {self.name} {self.labels}: {self.value}'


async def send_telemetry(telemetry_data: TelemetryEvent | TelemetryMeasurement) -> None:
    if not settings.SEND_PLATFORM_METRICS_DATA:
        log.debug('Skip sending telemetry: %s', telemetry_data)
        return

    if isinstance(telemetry_data, TelemetryMeasurement):
        endpoint = settings.SMP_PLATFORM_METRICS_MEASUREMENTS_URL
    elif isinstance(telemetry_data, TelemetryEvent):
        endpoint = settings.SMP_PLATFORM_METRICS_EVENTS_URL
    else:
        raise TypeError(f'Expected TelemetryEvent or TelemetryMeasurement, got {type(telemetry_data).__name__}')

    if not telemetry_data.labels:
        log.warning('%s has no labels, skipping.', telemetry_data)
        return

    try:
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(
                settings.SMP_APP_ID,
                settings.SMP_APP_SECRET,
            ),
        ) as session:
            log.debug('Sending metric %s to %s', asdict(telemetry_data), '/'.join((settings.SMP_BASE_URL, endpoint)))
            async with session.post(
                '/'.join((settings.SMP_BASE_URL, endpoint)),
                json=asdict(telemetry_data),
            ) as res:
                if res.status not in (200, 201):
                    content = await res.content.read()
                    log.exception('SMP-platform-metrics responded with %s: %s on telemetry data: %s',
                                  res.status, content, asdict(telemetry_data))
    except Exception as exc:
        log.exception('Failed to send to PlatformMetrics: %s', exc)


class SendUserActionEventDecorator:
    """
    Decorator to send telemetry from Bot module
    """
    def __init__(self, **labels):
        self.labels = labels

    def __call__(self, func):
        async def wrapped_func(*args, **kwargs):
            update = next(filter(lambda arg: isinstance(arg, (CallbackQuery, Message)), args), None)

            # skip not BotModule methods
            if not update:
                return await func(*args, **kwargs)

            action_entity, action_type = self._get_action_entity_and_type(update)
            result_status = EventLabelResultStatusValue.success

            if not getattr(update.from_user, 'id', None):
                return await func(*args, **kwargs)

            user_id = update.from_user.id

            try:
                return await func(*args, **kwargs)
            # these errors are skippable
            except exceptions.EmptyResultsException:
                result_status = EventLabelResultStatusValue.empty
                raise
            # TODO inherit errors from one class
            except (exceptions.AccountIsPrivate, exceptions.AccountNotExist, exceptions.WrongInputException):
                result_status = EventLabelResultStatusValue.wrong_input
                raise
            except Exception:
                result_status = EventLabelResultStatusValue.error
                raise  # pass to decorator above
            finally:
                labels_kwargs = dict(
                    action_entity=action_entity,
                    action_type=action_type,
                    in_conversation=await redis_connector.get_user_data('conversation', user_id),
                    status=result_status,
                )
                labels_kwargs.update(**self.labels)  # override with explicit values
                await send_telemetry(
                    TelemetryEvent(
                        event_labels=UserActionEventLabels(**labels_kwargs),
                        event_name=TelemetryEventName.tgbot_user_action_event,
                    ))
        return wrapped_func

    @staticmethod
    def _get_action_entity_and_type(update: CallbackQuery | Message) -> Tuple[str]:
        action_entity = None
        action_type = None

        if isinstance(update, CallbackQuery):
            # define `action_entity` explicitly
            action_type = EventLabelUserActionTypeValue.button_pressed
        elif command := getattr(update, 'command', None):
            action_entity = command[0]  # command text
            action_type = EventLabelUserActionTypeValue.send_command
        elif media_type := getattr(update, 'media', None):
            action_entity = media_type  # 'photo', 'video', etc
            action_type = EventLabelUserActionTypeValue.send_media
        elif getattr(update, 'text', None):
            action_type = EventLabelUserActionTypeValue.send_text

        return action_entity, action_type
