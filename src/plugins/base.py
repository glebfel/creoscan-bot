import importlib
from typing import Optional

from pyrogram import Client
from pyrogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardMarkup,
)

import settings
from addons.Permissions import restricted_method_decorator
from helpers.state import redis_connector
from models import Module


def get_active_modules() -> list:
    active_modules = []
    for plugin_path in settings.PLUGINS:
        active_modules.append(getattr(importlib.import_module(f'plugins.{plugin_path}'), 'module', None))
    return active_modules


def get_modules_buttons() -> list:
    return list(filter(lambda s: s.strip(), [' '.join([
        getattr(mod, 'icon', '') or '',
        getattr(mod, 'friendly_name', '') or '',
    ]) for mod in get_active_modules()]))


def get_modules_commands() -> list:
    return [f'/{c}' for c in list(filter(lambda s: s.strip(), [
        getattr(mod, 'command', '') or '' for mod in get_active_modules()
    ]))]


@restricted_method_decorator
async def callback(client: Client, module: Module, update: CallbackQuery | Message) -> None:
    """
    Base entry point to the module, responses with some introduction text
    and sets user's context to the module.
    """

    # response with modules's introduction text
    await update.reply(
        text=module.introduction_text,
        reply_markup=module.keyboard if hasattr(module, 'keyboard') else None,
        disable_web_page_preview=True,
    )

    # store identifier in which conversation user is
    await redis_connector.save_user_data(
        key='conversation',
        data=module.name,
        user_id=update.from_user.id,
    )
