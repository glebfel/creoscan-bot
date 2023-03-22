from dataclasses import dataclass, asdict

from common.models import ThirdPartyAPISource
from helpers.clients import InstagramRapidAPIClient, TikTokRapidAPIClient
from helpers.state import redis_connector
from models import BotModule


@dataclass
class UserMonitoringRequest:
    user_id: int
    nickname: str = None
    social_network: str = None
    active: bool = False
    selected_media_type: str = None
    start_date: str = None


class UserMonitoringRequestsDBConnector:
    """
    Handle user's monitoring requests using redis.
    """

    @staticmethod
    async def save_user_monitoring(user_request: UserMonitoringRequest, new=False) -> None:
        if new:
            request_list = await redis_connector.get_data(key=str(user_request.user_id))
            if not request_list:
                await redis_connector.save_data(key=str(user_request.user_id), data=[asdict(user_request)])
            else:
                request_list.append(asdict(user_request))
                await redis_connector.save_data(key=str(user_request.user_id), data=request_list)
        else:
            request_list = await redis_connector.get_data(key=str(user_request.user_id))
            request_list[-1].update((k, v) for k, v in asdict(user_request).items() if v is not None)
            await redis_connector.save_data(key=str(user_request.user_id), data=request_list)

    @staticmethod
    async def get_last_user_monitoring(user_id: int) -> UserMonitoringRequest:
        requests = await redis_connector.get_data(key=str(user_id))
        if requests:
            return UserMonitoringRequest(**requests[-1])

    @staticmethod
    async def get_all_user_monitorings(user_id: int) -> list[UserMonitoringRequest]:
        requests = await redis_connector.get_data(key=str(user_id))
        if not requests:
            return []
        return [UserMonitoringRequest(**_) for _ in requests]

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


def get_monitoring_handler(module: BotModule, social_network: str, media_type: str) -> callable:
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
