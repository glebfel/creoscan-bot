import logging
import pathlib

import yaml
from collections import ChainMap
from dataclasses import dataclass, field, fields

import settings


log = logging.getLogger(__name__)

# root directory
ROOT_PATH = str(pathlib.Path(__file__).parent.parent) + '\\'


def read_external_config(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as file:
        loaded_docs = [doc for doc in yaml.safe_load_all(file) if doc]

    # combine list of dicts into one dict
    return dict(ChainMap(*loaded_docs))


loaded_config = read_external_config(ROOT_PATH + settings.CONFIG_PATH)


@dataclass
class Module:
    name: str

    current_module_text: str = field(init=False)
    help_command_text: str = field(init=False)
    unknown_command_text: str = field(init=False)
    unhandled_error_text: str = field(init=False)
    wrong_input_text: str = field(init=False)

    def __post_init__(self):
        # assign data from config to self fields if module name and field name are
        # declared in external config
        for field_ in {f.name for f in fields(self) if not f.init}:
            if (module_config := loaded_config.get(self.name)):
                setattr(self, field_, module_config.get(field_, None))


@dataclass
class BotModule(Module):
    command: str = field(init=False)
    description: str = field(init=False)
    friendly_name: str = field(init=False)
    icon: str = field(init=False)
    introduction_text: str = field(init=False)
    header_text: str = field(init=False)
    footer_text: str = field(init=False)

    @property
    def button(self):
        return ' '.join((self.icon or '', self.friendly_name or ''))
