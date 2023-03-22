from helpers.state import redis_connector


class UserMonitoringRequests:
    """
    Handle user's monitoring requests using redis.
    """
    @staticmethod
    async def save_user_request(user_id: int, new=False, **kwargs) -> None:
        if new:
            request_list = await redis_connector.get_data(key=str(user_id))
            if not request_list:
                await redis_connector.save_data(key=str(user_id), data=[kwargs])
            else:
                request_list.append(kwargs)
                await redis_connector.save_data(key=str(user_id), data=request_list)
        else:
            request_list = await redis_connector.get_data(key=str(user_id))
            request_list[-1].update(kwargs)
            await redis_connector.save_data(key=str(user_id), data=request_list)

    @staticmethod
    async def get_last_user_request(user_id: int) -> dict:
        requests = await redis_connector.get_data(key=str(user_id))
        if requests:
            return requests[-1]

    @staticmethod
    async def get_user_requests(user_id: int) -> list[dict]:
        requests = await redis_connector.get_data(key=str(user_id))
        if not requests:
            return []
        return requests

    @staticmethod
    async def get_user_request_by_nickname_and_social(user_id: int, social_network: str, nickname: str) -> dict | None:
        requests = await UserMonitoringRequests.get_user_requests(user_id)
        for _ in requests:
            if _['social_network'] == social_network and _['nickname'] == nickname:
                return _

    @staticmethod
    async def delete_user_request_by_nickname_and_social(user_id: int, social_network: str, nickname: str) -> None:
        requests = await UserMonitoringRequests.get_user_requests(user_id)
        for _ in requests:
            if _['social_network'] == social_network and _['nickname'] == nickname:
                return requests.remove(_)
        await redis_connector.save_data(key=str(user_id), data=requests)