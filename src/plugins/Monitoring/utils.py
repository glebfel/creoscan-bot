import datetime
from dataclasses import dataclass, asdict, field

from apscheduler.triggers.cron import CronTrigger

from common.models import ThirdPartyAPISource, ThirdPartyAPIMediaItem
from helpers.clients import InstagramRapidAPIClient, TikTokRapidAPIClient
from helpers.state import redis_connector
from models import BotModule


@dataclass
class UserMonitoringRequest:
    user_id: int
    nickname: str = None
    social_network: str = None
    active: bool = None
    selected_media_type: str | None = None
    start_date: str = None
    is_confirmed: bool = None


@dataclass
class UserMonitoringJob:
    user_id: int
    data: ThirdPartyAPIMediaItem = None
    last_updated_at: datetime.datetime = field(default=datetime.datetime.now())


class UserMonitoringRequestsDBConnector:
    """
    Handle user's monitoring requests using redis.
    """

    @staticmethod
    async def save_user_monitoring(user_request: UserMonitoringRequest, new=False) -> None:
        if new:
            # delete old not confirmed monitorings
            if monitoring_requests := await redis_connector.get_data(key=str(user_request.user_id)):
                for i in monitoring_requests:
                    user_request = UserMonitoringRequest(**i)
                    if not user_request.is_confirmed:
                        await UserMonitoringRequestsDBConnector.delete_user_monitoring_by_nickname_and_social(
                            user_request.user_id,
                            nickname=user_request.nickname,
                            social_network=user_request.social_network
                        )

            if not monitoring_requests:
                await redis_connector.save_data(key=str(user_request.user_id), data=[asdict(user_request)])
            else:
                monitoring_requests.append(asdict(user_request))
                await redis_connector.save_data(key=str(user_request.user_id), data=monitoring_requests)
        else:
            monitoring_requests = await redis_connector.get_data(key=str(user_request.user_id))
            monitoring_requests[-1].update((k, v) for k, v in asdict(user_request).items() if v is not None or
                                           k == "selected_media_type")
            await redis_connector.save_data(key=str(user_request.user_id), data=monitoring_requests)

    @staticmethod
    async def get_last_user_monitoring(user_id: int) -> UserMonitoringRequest:
        requests = await redis_connector.get_data(key=str(user_id))
        if requests:
            return UserMonitoringRequest(**requests[-1])

    @staticmethod
    async def confirm_last_user_monitoring(user_id: int):
        await UserMonitoringRequestsDBConnector.save_user_monitoring(UserMonitoringRequest(user_id=user_id,
                                                                                           is_confirmed=True))

    @staticmethod
    async def activate_last_user_monitoring(user_id: int):
        # made user monitoring request active
        await UserMonitoringRequestsDBConnector.save_user_monitoring(
            UserMonitoringRequest(
                user_id=user_id,
                start_date=datetime.datetime.now().strftime('%d.%m.%Y'),
                active=True
            ))

    @staticmethod
    async def deactivate_last_user_monitoring(user_id: int):
        await UserMonitoringRequestsDBConnector.save_user_monitoring(
            UserMonitoringRequest(
                user_id=user_id,
                active=False
            ))

    @staticmethod
    async def get_all_user_monitorings(user_id: int) -> list[UserMonitoringRequest]:
        actual_monitorings = []
        if monitoring_requests := await redis_connector.get_data(key=str(user_id)):
            for i in monitoring_requests:
                user_request = UserMonitoringRequest(**i)
                if user_request.is_confirmed:
                    actual_monitorings.append(user_request)
        return actual_monitorings

    @staticmethod
    async def get_user_monitoring_by_nickname_and_social(user_id: int, social_network: str,
                                                         nickname: str) -> UserMonitoringRequest | None:
        requests = await UserMonitoringRequestsDBConnector.get_all_user_monitorings(user_id)
        for _ in requests:
            if _.social_network == social_network and _.nickname == nickname:
                return _

    @staticmethod
    async def delete_user_monitoring_by_nickname_and_social(user_id: int, social_network: str, nickname: str) -> None:
        requests = await UserMonitoringRequestsDBConnector.get_all_user_monitorings(user_id)
        for _ in requests:
            if _.social_network == social_network and _.nickname == nickname:
                requests.remove(_)
        await redis_connector.save_data(key=str(user_id), data=[asdict(_) for _ in requests])

    @staticmethod
    async def get_last_updated_monitoring_data(user_id: int) -> UserMonitoringJob:
        # get last media data from storage
        monitoring_data = await redis_connector.get_user_data(
            key='monitoring_last_updated_media',
            user_id=user_id,
        )
        monitoring_data = ThirdPartyAPIMediaItem(**monitoring_data) if monitoring_data else None
        # get last monitoring update date from storage
        last_update_date = await redis_connector.get_user_data(
            key='monitoring_last_updated_date',
            user_id=user_id,
        )
        last_update_date = last_update_date if last_update_date else datetime.datetime.now()
        return UserMonitoringJob(user_id=user_id, data=monitoring_data, last_updated_at=last_update_date)

    @staticmethod
    async def save_last_updated_monitoring_data(data: ThirdPartyAPIMediaItem, user_id: int):
        # save media data
        await redis_connector.save_user_data(
            key='monitoring_last_updated_media',
            data=asdict(data),
            user_id=user_id,
        )
        # save last update date
        await redis_connector.save_user_data(
            key='monitoring_last_updated_date',
            data=datetime.datetime.now(),
            user_id=user_id,
        )


def get_monitoring_media_handler_func(module: BotModule, social_network: str, media_type: str) -> callable:
    if social_network == ThirdPartyAPISource.instagram.value:
        match media_type:
            case module.reels_button:
                return InstagramRapidAPIClient().get_instagram_reels_by_username
            case module.posts_button:
                return InstagramRapidAPIClient().get_instagram_posts_by_username
            case module.stories_button:
                return InstagramRapidAPIClient().get_instagram_user_stories
    else:
        return TikTokRapidAPIClient().get_tiktok_user_videos_by_username


def seconds_to_cron(interval_seconds: int) -> CronTrigger:
    # Calculate time components
    minutes, seconds = divmod(interval_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        if minutes > 0:
            return CronTrigger(
                minute='*/{}'.format(minutes),
                hour='*/{}'.format(hours),
            )
        return CronTrigger(
            hour='*/{}'.format(hours),
        )
    elif minutes > 0:
        if seconds > 0:
            return CronTrigger(
                minute='*/{}'.format(minutes),
                second='*/{}'.format(seconds),
            )
        return CronTrigger(
            minute='*/{}'.format(minutes),
        )
    return CronTrigger(second='*/{}'.format(seconds) if seconds > 0 else '*')
