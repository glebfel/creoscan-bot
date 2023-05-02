import datetime
from dataclasses import dataclass, field

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)

import settings
from addons.Trottling import handle_trottling_decorator
from common.decorators import (
    inform_user_decorator, handle_common_exceptions_decorator,
)
from common.filters import conversation_filter
from common.models import ThirdPartyAPISource, ThirdPartyAPIMediaItem, ThirdPartyAPIMediaType, ThirdPartyAPIClientAnswer
from helpers.state import redis_connector
from helpers.utils import extract_username_from_link
from plugins.Monitoring.jobs import monitoring_scheduler
from plugins.Monitoring.jobs import start_monitoring
from models import BotModule
from plugins.Monitoring.utils import UserMonitoringRequestsDBConnector, UserMonitoringRequest, seconds_to_cron
from plugins.base import get_modules_buttons


@dataclass
class MonitoringModule(BotModule):
    # to store client in memory
    tg_client = None

    instagram_media_type_choice_text: str = field(init=False)
    subscribe_confirmation_text: str = field(init=False)
    subscribe_text: str = field(init=False)
    monitoring_requests_exceed_error_text: str = field(init=False)

    my_monitoring_command: str = field(init=False)
    my_monitoring_active_introduction_text: str = field(init=False)
    my_monitoring_not_active_introduction_text: str = field(init=False)
    pause_monitoring_text: str = field(init=False)
    restart_monitoring_text: str = field(init=False)
    delete_confirmation_text: str = field(init=False)
    delete_text: str = field(init=False)
    edit_my_monitoring_text: str = field(init=False)
    create_monitoring_button: str = field(init=False)

    return_button: str = field(init=False)
    my_monitoring_button: str = field(init=False)
    button_selected: str = field(init=False)
    button_unselected: str = field(init=False)
    subscribe_button: str = field(init=False)
    stories_button: str = field(init=False)
    posts_button: str = field(init=False)
    reels_button: str = field(init=False)

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        support_button = get_modules_buttons()[-1]
        buttons = [self.my_monitoring_button, support_button, self.return_button, ]
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

    @property
    def result_keyboard(self) -> InlineKeyboardMarkup:
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
        Buttons for ReplyKeyboardMarkup should be in form of:
        [ (button1, button2), (button3, button4), ... ]
        """
        buttons_in_columns.append(extra_buttons)

        return ReplyKeyboardMarkup(
            list(buttons_in_columns),
            one_time_keyboard=False,
            placeholder=self.friendly_name,
            resize_keyboard=True,
        )


module = MonitoringModule('monitoring')


@Client.on_callback_query(filters.regex('^RETURN_TO_MONITORING'))
@Client.on_message(filters.regex(rf'^{module.my_monitoring_button}$') |
                   filters.command(module.my_monitoring_command))
@handle_common_exceptions_decorator
async def handle_my_monitoring(client: Client, update: CallbackQuery | Message) -> None:
    user_requests = await UserMonitoringRequestsDBConnector.get_all_user_monitorings(user_id=update.from_user.id)
    if isinstance(update, CallbackQuery):
        update = update.message

    if len(user_requests) > 0:
        text = module.my_monitoring_active_introduction_text.format(
            available_count=settings.FREE_MONITORING_REQUESTS_COUNT - len(user_requests),
            max_count=settings.FREE_MONITORING_REQUESTS_COUNT)

        # generate keyboard from subscriptions
        markup = []
        for sub in user_requests:
            markup.append([InlineKeyboardButton(text=f'({sub.social_network.capitalize()}) {sub.nickname}',
                                                callback_data=f'account_{sub.nickname}_{sub.social_network}')])

        await update.reply_text(text=text, reply_markup=InlineKeyboardMarkup(markup))
    else:
        text = module.my_monitoring_not_active_introduction_text.format(
            available_count=settings.FREE_MONITORING_REQUESTS_COUNT - len(user_requests),
            max_count=settings.FREE_MONITORING_REQUESTS_COUNT)

        await update.reply_text(text=text, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(module.create_monitoring_button, callback_data=module.create_monitoring_button)],
             [InlineKeyboardButton(module.return_button, callback_data=module.return_button)]]))


@Client.on_callback_query(filters.regex('^account') | filters.regex('^RETURN_TO_EDIT'))
async def edit_my_monitoring_request(client: Client, callback_query: CallbackQuery) -> None:
    if 'RETURN_TO_EDIT' in callback_query.data:
        user_data = callback_query.data.replace('RETURN_TO_EDIT_', '').split('_')
        social_network = user_data[-1]
        nickname = '_'.join([_ for _ in user_data if _ != social_network])
    else:
        user_data = callback_query.data.replace('account_', '').split('_')
        social_network = user_data[-1]
        nickname = '_'.join([_ for _ in user_data if _ != social_network])

    monitoring = await UserMonitoringRequestsDBConnector.get_user_monitoring_by_nickname_and_social(
        callback_query.from_user.id,
        nickname=nickname,
        social_network=social_network)

    text = module.edit_my_monitoring_text.format(
        nickname=monitoring.nickname,
        social_network=social_network.capitalize(),
        media_type=monitoring.selected_media_type,
        active='активен' if monitoring.active else 'не активен',
        start_date=monitoring.start_date.strftime('%d.%m.%Y'),)

    # generate keyboard
    action_button = InlineKeyboardButton(text='Остановить', callback_data=f'PAUSE_{nickname}_{social_network}') \
        if monitoring.active \
        else InlineKeyboardButton(text='Запустить', callback_data=f'RESTART_{nickname}_{social_network}')
    markup = InlineKeyboardMarkup(
        [[action_button,
          InlineKeyboardButton(text='Удалить', callback_data=f'DELETE_{nickname}_{social_network}')],
         [InlineKeyboardButton(text='<< Вернуться к мониторингам', callback_data='RETURN_TO_MONITORING')]])

    await callback_query.message.edit_text(text=text, reply_markup=markup)


@Client.on_callback_query(filters.regex('^RESTART'))
async def restart_my_monitoring_request(client: Client, callback_query: CallbackQuery) -> None:
    user_data = callback_query.data.replace('RESTART_', '').split('_')
    social_network = user_data[-1]
    nickname = '_'.join([_ for _ in user_data if _ != social_network])

    monitoring = await UserMonitoringRequestsDBConnector.get_user_monitoring_by_nickname_and_social(
        callback_query.from_user.id,
        nickname=nickname,
        social_network=social_network)

    # activate monitoring in redis
    await UserMonitoringRequestsDBConnector.activate_last_user_monitoring(callback_query.from_user.id)

    # pause monitoring job
    monitoring_scheduler.resume_job(
        job_id=f'monitoring-{callback_query.from_user.id}-{social_network}-{nickname}'
    )

    # generate keyboard
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='<< Вернуться к мониторингам', callback_data='RETURN_TO_MONITORING')]])

    text = module.restart_monitoring_text.format(
        nickname=monitoring.nickname, )
    await callback_query.message.edit_text(text=text, reply_markup=markup)


@Client.on_callback_query(filters.regex('^PAUSE'))
async def pause_my_monitoring_request(client: Client, callback_query: CallbackQuery) -> None:
    user_data = callback_query.data.replace('PAUSE_', '').split('_')
    social_network = user_data[-1]
    nickname = '_'.join([_ for _ in user_data if _ != social_network])

    monitoring = await UserMonitoringRequestsDBConnector.get_user_monitoring_by_nickname_and_social(
        callback_query.from_user.id,
        nickname=nickname,
        social_network=social_network)

    # pause monitoring in redis
    await UserMonitoringRequestsDBConnector.deactivate_last_user_monitoring(callback_query.from_user.id)

    # pause monitoring job
    monitoring_scheduler.pause_job(
        job_id=f'monitoring-{callback_query.from_user.id}-{social_network}-{nickname}'
    )

    # generate keyboard
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='<< Вернуться к мониторингам', callback_data='RETURN_TO_MONITORING')]])

    text = module.pause_monitoring_text.format(
        nickname=monitoring.nickname, )
    await callback_query.message.edit_text(text=text, reply_markup=markup)


@Client.on_callback_query(filters.regex('^DELETE'))
async def delete_confirmation_my_monitoring_request(client: Client, callback_query: CallbackQuery) -> None:
    user_data = callback_query.data.replace('DELETE_', '').split('_')
    social_network = user_data[-1]
    nickname = '_'.join([_ for _ in user_data if _ != social_network])

    text = module.delete_confirmation_text.format(
        nickname=nickname, )

    # generate keyboard
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='Нет, забудь', callback_data=f'RETURN_TO_EDIT_{nickname}_{social_network}')],
         [InlineKeyboardButton(text='Да, я уверен', callback_data=f'CONFIRM_DELETE_{nickname}_{social_network}')],
         [InlineKeyboardButton(text='<< Вернуться к редактированию',
                               callback_data=f'RETURN_TO_EDIT_{nickname}_{social_network}')]])

    await callback_query.message.edit_text(text=text, reply_markup=markup)


@Client.on_callback_query(filters.regex('^CONFIRM_DELETE'))
async def delete_my_monitoring_request(client: Client, callback_query: CallbackQuery) -> None:
    user_data = callback_query.data.replace('CONFIRM_DELETE_', '').split('_')
    social_network = user_data[-1]
    nickname = '_'.join([_ for _ in user_data if _ != social_network])

    # delete monitoring in redis
    await UserMonitoringRequestsDBConnector.delete_user_monitoring_by_nickname_and_social(callback_query.from_user.id,
                                                                                          nickname=nickname,
                                                                                          social_network=social_network)

    # delete monitoring job
    monitoring_scheduler.remove_job(
        job_id=f'monitoring-{callback_query.from_user.id}-{social_network}-{nickname}'
    )

    text = module.delete_text.format(
        nickname=nickname, )

    # generate keyboard
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text='<< Вернуться к мониторингам', callback_data='RETURN_TO_MONITORING')]])

    await callback_query.message.edit_text(text=text, reply_markup=markup)


@Client.on_callback_query(filters.regex(rf'^{module.return_button}$') |
                          filters.regex(rf'^{module.create_monitoring_button}$'))
@Client.on_message(filters.regex(rf'^{module.button}$') | filters.command(module.command))
@inform_user_decorator
@handle_trottling_decorator
@handle_common_exceptions_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    MonitoringModule.tg_client = client

    # response with modules's introduction text
    user_requests = await UserMonitoringRequestsDBConnector.get_all_user_monitorings(update.from_user.id)

    # store identifier in which conversation user is
    await redis_connector.save_user_data(
        key='conversation',
        data=module.name,
        user_id=update.from_user.id,
    )

    if isinstance(update, CallbackQuery):
        update = update.message

    await update.reply(
        text=module.introduction_text.format(
            available_count=settings.FREE_MONITORING_REQUESTS_COUNT - len(user_requests),
            max_count=settings.FREE_MONITORING_REQUESTS_COUNT),
        reply_markup=module.keyboard if hasattr(module, 'keyboard') else None,
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex('^SUBSCRIBE'))
@handle_common_exceptions_decorator
async def handle_subscribe(client: Client, callback_query: CallbackQuery) -> None:
    # confirm monitoring
    await UserMonitoringRequestsDBConnector.confirm_last_user_monitoring(callback_query.from_user.id)

    # extract user data from redis
    user_data = await UserMonitoringRequestsDBConnector.get_last_user_monitoring(callback_query.from_user.id)

    # made user monitoring request active
    await UserMonitoringRequestsDBConnector.activate_last_user_monitoring(callback_query.from_user.id)

    start_time = datetime.datetime.now()
    if current_jobs := monitoring_scheduler.get_jobs():
        channel_stats_jobs = list(filter(lambda j: j.id.startswith('monitoring'), current_jobs))
        if channel_stats_jobs:
            last_job = channel_stats_jobs[-1]
            start_time = last_job.next_run_time

    start_time += datetime.timedelta(seconds=settings.PENDING_DELAY)

    monitoring_scheduler.add_job(
        start_monitoring,
        trigger=seconds_to_cron(settings.SEND_MONITORING_INTERVAL_SECONDS),
        id=f'monitoring-{user_data.user_id}-{user_data.social_network}-{user_data.nickname}',
        name=f'Monitoring for {user_data.nickname} by {user_data.user_id}',
        misfire_grace_time=None,
        kwargs={
            'message_handler': send_monitoring_message_to_user,
            'module': module,
            'message': callback_query.message,
            'social_network': user_data.social_network,
            'nickname': user_data.nickname,
            'media_type': user_data.selected_media_type
        },
    )

    text = module.subscribe_text.format(
        social_network=user_data.social_network.capitalize(),
        nickname=user_data.nickname, )

    await callback_query.message.reply_text(text=text)


@Client.on_callback_query(filters.regex('^CONFIRM_SUBSCRIBE'))
@handle_common_exceptions_decorator
async def handle_subscribe_confirmation(client: Client, callback_query: CallbackQuery) -> None:
    # extract user data from redis
    user_data = await UserMonitoringRequestsDBConnector.get_last_user_monitoring(user_id=callback_query.from_user.id)

    text = module.subscribe_confirmation_text.format(
        social_network=user_data.social_network.capitalize(),
        nickname=user_data.nickname,
        media_list=f'✸ {user_data.selected_media_type}\n')

    await callback_query.message.reply_text(text=text,
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(module.subscribe_button,
                                                                       callback_data='SUBSCRIBE')]]))


@Client.on_callback_query(filters.regex('^SELECT'))
@handle_common_exceptions_decorator
async def choose_media_type(client: Client, callback_query: CallbackQuery) -> None:
    """
    Handles include/exclude button. Redraws original message with the
    same, and changes entity (e.g. emoji) that represents selected hashtag.
    """
    # stashed hashtags contains only selected by user
    selected_media_type = callback_query.data.replace('SELECT', '')

    user_request = await UserMonitoringRequestsDBConnector.get_last_user_monitoring(user_id=callback_query.from_user.id)
    if user_request.selected_media_type == selected_media_type:
        # clean by made media type equals to unknown
        selected_media_type = ThirdPartyAPIMediaType.unknown
    # save media type to redis storage
    await UserMonitoringRequestsDBConnector.save_user_monitoring(
        UserMonitoringRequest(
            user_id=callback_query.from_user.id,
            selected_media_type=selected_media_type))

    await callback_query.message.edit_reply_markup(
        get_keyboard_select_media_type(
            selected=selected_media_type,
            social_network=ThirdPartyAPISource.instagram.value
        ))


def get_keyboard_select_media_type(social_network: ThirdPartyAPISource,
                                   selected: str | None = None) -> InlineKeyboardMarkup:
    if social_network == ThirdPartyAPISource.instagram:
        media_type_buttons = [
            [
                InlineKeyboardButton(
                    media_type,  # actually max for Tg button is 64
                    callback_data='PASS',  # button press will do nothing
                ),
                InlineKeyboardButton(
                    module.button_selected if str(
                        media_type
                    ) == selected else module.button_unselected,
                    callback_data=f'SELECT{str(media_type)}',
                ),
            ] for media_type in (module.stories_button, module.posts_button, module.reels_button)
        ]
        markup = [
            *media_type_buttons,
        ]
        if selected:
            markup.append([InlineKeyboardButton(module.subscribe_button, callback_data='CONFIRM_SUBSCRIBE')], )

    else:
        markup = [
            [InlineKeyboardButton(module.subscribe_button, callback_data='SUBSCRIBE')],
        ]
    return InlineKeyboardMarkup(markup)


@Client.on_message(filters.text & conversation_filter(module.name))
@handle_trottling_decorator
@handle_common_exceptions_decorator
@inform_user_decorator
async def handle_user_link_input(client: Client, message: Message) -> None:
    # check if user is already subscribed
    user_requests = await UserMonitoringRequestsDBConnector.get_all_user_monitorings(message.from_user.id)
    if len(user_requests) >= settings.FREE_MONITORING_REQUESTS_COUNT:
        text = module.monitoring_requests_exceed_error_text.format(
            available_count=settings.FREE_MONITORING_REQUESTS_COUNT - len(user_requests),
            max_count=settings.FREE_MONITORING_REQUESTS_COUNT)
        await message.reply_text(text=text,
                                 reply_markup=ReplyKeyboardMarkup([[module.return_button]], resize_keyboard=True))
        return

    nickname = extract_username_from_link(message)

    if 'tiktok' in message.text.lower():
        social_network = ThirdPartyAPISource.tiktok.value

        await message.reply_text(
            text=module.subscribe_confirmation_text.format(nickname=nickname,
                                                           social_network=ThirdPartyAPISource.tiktok.value.capitalize(),
                                                           media_list=f'✸ Видео'),
            reply_markup=get_keyboard_select_media_type(social_network=ThirdPartyAPISource.tiktok))

        await UserMonitoringRequestsDBConnector.save_user_monitoring(
            UserMonitoringRequest(user_id=message.from_user.id,
                                  nickname=nickname,
                                  selected_media_type='Видео',
                                  social_network=social_network),
            new=True)

    else:
        social_network = ThirdPartyAPISource.instagram.value
        await message.reply_text(
            text=module.instagram_media_type_choice_text.format(nickname=nickname),
            reply_markup=get_keyboard_select_media_type(social_network=ThirdPartyAPISource.instagram))

        await UserMonitoringRequestsDBConnector.save_user_monitoring(
            UserMonitoringRequest(user_id=message.from_user.id,
                                  nickname=nickname,
                                  social_network=social_network),
            new=True)


async def send_monitoring_message_to_user(chat_id: int, message: str, media: ThirdPartyAPIClientAnswer = None) -> None:
    if MonitoringModule.tg_client:
        if media:
            for item in media.items:
                match item.media_type:
                    case ThirdPartyAPIMediaType.photo:
                        await MonitoringModule.tg_client.send_photo(
                            chat_id=chat_id,
                            caption=message,
                            photo=item.media_url,
                            reply_markup=module.result_keyboard,
                        )
                    case ThirdPartyAPIMediaType.video:
                        await MonitoringModule.tg_client.send_video(
                            chat_id=chat_id,
                            caption=message,
                            video=item.media_url,
                            reply_markup=module.result_keyboard,
                        )
        else:
            await MonitoringModule.tg_client.send_message(chat_id=chat_id, text=message)
