import importlib
import logging
from dataclasses import dataclass

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardMarkup,
)

import settings
from addons.Trottling import handle_trottling_decorator  # type: ignore
from common.decorators import handle_common_exceptions_decorator  # type: ignore
from common.models import UserRoleBit  # type: ignore
from models import BotModule  # type: ignore

from ..base import callback as base_callback


log = logging.getLogger(__name__)


def get_active_modules() -> list:
    active_modules = []
    for plugin_path in settings.PLUGINS:
        module = getattr(importlib.import_module(f'plugins.{plugin_path}'), 'module', None)
        if hasattr(module, 'allowed_role'):
            active_modules.append(module)
    return active_modules


def get_modules_buttons() -> list:
    return list(filter(lambda s: s.strip(), [' '.join([
        getattr(mod, 'icon', '') or '',
        getattr(mod, 'friendly_name', '') or '',
    ]).strip() for mod in get_active_modules()]))


def get_modules_commands() -> list:
    return [f'/{c}' for c in list(filter(lambda s: s.strip(), [
        getattr(mod, 'command', '') or '' for mod in get_active_modules()
    ]))]


@dataclass
class AdminModule(BotModule):
    allowed_role = UserRoleBit.admin
    command = 'admin'
    description = 'Admin module'
    friendly_name = ''
    icon = ''

    header_text = 'hhh'
    footer_text = 'fff'
    pending_text = 'ppp'
    result_text = 'rrr'

    current_module_text = 'Вы находитесь в модуле {}.'
    help_command_text = 'HELP ADMIN TEXT'
    unknown_command_text = 'UNKNOWN ADMIN TEXT'
    unhandled_error_text = 'UNHA ADMIN TEXT'
    wrong_input_text = 'WRONG INP ADMIN TEXT'
    introduction_text = ((
        'Добро пожаловать в модуль для **администраторов**.\n\n'
        'Доступные операции можно выбрать через нижнее меню.\n'
        'Чтобы покинуть модуль, введи /start\n\n'
        '__И помни: с великой силой приходит великая ответственность!__'
    ))

    @property
    def keyboard(self) -> ReplyKeyboardMarkup:
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


module = AdminModule(name='admin')


@Client.on_message(filters.command('admin'))
@handle_common_exceptions_decorator
@handle_trottling_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)
