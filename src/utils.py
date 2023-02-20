import datetime
import inspect
import logging
import time
from typing import Any, Callable, Optional

from common.models import UserRoleBit
from helpers.state import redis_connector, StashKeys

log = logging.getLogger(__name__)


async def check_permission(role: Optional[int], allowed_role: Optional[UserRoleBit]) -> bool:
    if allowed_role is None:
        # assume action is allowed for everyone
        return True

    if role is None:
        # assume user has no role, so any restricted actions are forbidden
        return False

    """
    User role is a sequence of bits, e.g. 0010.
    If user has permission for a particular role, corresponding bit is set to 1.
    Positions of the bits (i.e. roles) defined by `UserRoleBit`.
    """
    return role & (1 << allowed_role)


async def check_trottling(stash_key: StashKeys, window_size_s: float, user_id: int,
                          requests_limit: int = 2, on_counter_reset: Optional[Callable] = None) -> bool:
    # requests_limit = 2 is an optimal value for following logic
    # 1st excessive request is a warning
    # 2nd - trottling is applied

    now_timestamp = time.mktime((datetime.datetime.now()).timetuple())

    user_requests = await redis_connector.get_user_data(key=stash_key, user_id=user_id) or {}
    log.debug('Loaded user requests for user #%s: %s (now is %s)', user_id, user_requests, now_timestamp)

    # get saved window bound or set new window
    reset_at_timestamp = user_requests.get('reset_at', now_timestamp + window_size_s)

    requests_count = user_requests.get('count', 0)

    # user is 'outside' previous window, dump requests count to DB and reset it
    if reset_at_timestamp < now_timestamp:
        # do some additional stuff
        if on_counter_reset:
            await on_counter_reset(requests_count, user_id)
        requests_count = 0
        reset_at_timestamp = now_timestamp + window_size_s

        # clear `was_notifeid` flag to allow further notifications
        user_requests.pop('was_notified', None)

    # check if requests counter exceeded threshold
    requests_overhead = int(requests_count / requests_limit)

    # increase trottling wondow depending how significantly user exceeded limit
    # if they doesn't then window is kept the same
    reset_at_timestamp += window_size_s * requests_overhead

    user_requests.update({
        'count': requests_count + 1,
        'reset_at': reset_at_timestamp,
    })
    await redis_connector.save_user_data(
        key=stash_key,
        data=user_requests,
        user_id=user_id,
    )

    log.debug('User #%s requests limits: %s/%s in %s sec (overhead in %s times)',
              user_id,
              requests_count, requests_limit,
              window_size_s * requests_overhead or window_size_s,
              requests_overhead)

    # return exceeding status for further handling by others (e.g. sending a message)
    return bool(requests_overhead)


def get_module_classes(modules) -> list:
    """
    Some black magic here.
    `classes` contain a dict with all modules described in `modules` param (e.g. __init__.py from modules dir).
    `inspect.getsourcelines` returns an index of first module line of code in entire codebase.
    So, reversed list gives modules in import order.
    """
    classes = dict(inspect.getmembers(modules, inspect.isclass))
    return sorted(classes.values(), key=lambda x: inspect.getsourcelines(x)[1], reverse=True)


def validate_type(obj: Any, required_type: type) -> Any:
    if not isinstance(obj, required_type):
        if isinstance(required_type, tuple):
            expected = f'one of {", ".join(rt.__name__ for rt in required_type)}'
        else:
            expected = required_type.__name__
        raise TypeError(f'Expected {expected}, got {type(obj).__name__}')
    return obj


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
