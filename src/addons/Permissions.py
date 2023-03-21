import logging
from typing import Optional

from pyrogram import Client
from pyrogram.types import CallbackQuery, Message

from db.connector import database_connector
from common.models import UserRoleBit
from models import Module


log = logging.getLogger(__name__)


async def _check_permission(role: Optional[int], allowed_role: Optional[UserRoleBit]) -> bool:
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


def restricted_method_decorator(func):
    """
    Checks user permissions before executing the Handler method
    """
    async def wrapper(*args, **kwargs):
        if not any(isinstance(module := arg, Module) for arg in args):
            return await func(*args, **kwargs)

        if not any(isinstance(update := arg, (CallbackQuery, Message)) for arg in args):
            return await func(*args, **kwargs)

        if not any(isinstance(client := arg, Client) for arg in args):
            return await func(*args, **kwargs)

        allowed_role: UserRoleBit = getattr(module, 'allowed_role', None)
        # skip check for non-restricted modules
        if allowed_role is None:
            return await func(*args, **kwargs)

        user_role: int = (await database_connector.get_user(user_id=update.from_user.id)).role

        log.debug(
            'Checking user "%s" role "%s" before accessing module "%s" with restriction "%s"',
            update.from_user.id,
            user_role,
            module,
            allowed_role,
        )

        if not await _check_permission(user_role, allowed_role):
            log.warning('User "%s" has no access rights for module "%s"', update.from_user.id, module)
            # treat command as unknown if user is not allowed to use it
            #return await help_command(client, update)
            return  # TODO send help_message

        return await func(*args, **kwargs)

    return wrapper
