import logging
from dataclasses import dataclass, field

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)

from common.filters import (
    conversation_filter,
)
from addons.APIAdapter import WithHelperDecorator
from addons.Telemetry import SendUserActionEventDecorator
from addons.Trottling import (
    handle_paid_requests_trottling_decorator,
    handle_trottling_decorator,
)
from common.decorators import (
    handle_common_exceptions_decorator,
    inform_user_decorator,
)
from helpers.FeedAnalyzer import FeedAnalyzerHelper
from models import BotModule

from ..base import callback as base_callback


log = logging.getLogger(__name__)


@dataclass
class PublicationTimeModule(BotModule):
    result_text: str = field(init=False)
    button_contact: str = field(init=False)
    url_contact: str = field(init=False)

    @property
    async def share_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(self.button_contact, url=self.url_contact)]
        ])


module = PublicationTimeModule('best_publication_time')


@Client.on_message(filters.regex(rf'^{module.button}$') | filters.command(module.command))
@handle_common_exceptions_decorator
@handle_trottling_decorator
@SendUserActionEventDecorator(in_module=module.name)
@inform_user_decorator
async def callback(client: Client, update: CallbackQuery | Message) -> None:
    await base_callback(client, module, update)


@Client.on_message(filters.text & conversation_filter(module.name))
@handle_common_exceptions_decorator
@handle_paid_requests_trottling_decorator
@handle_trottling_decorator
@WithHelperDecorator(FeedAnalyzerHelper)
@SendUserActionEventDecorator(in_module=module.name)
@inform_user_decorator
async def handle_word(client: Client, message: Message, helper_data: dict = {}) -> None:
    text = module.result_text.format(
        posts_count=helper_data.posts_count,
        feed_since=helper_data.oldest_post_date.strftime('%d-%m-%Y'),
        feed_until=helper_data.newest_post_date.strftime('%d-%m-%Y'),
        best_post_url=helper_data.post_with_best_activity.link,
        worst_post_url=helper_data.post_with_worst_activity.link,
        average_likes_count=helper_data.average_likes_count,
        average_comments_count=helper_data.average_comments_count,
        best_first_publication_time=helper_data.best_first_publication_time.strftime('%H:%M'),
        best_second_publication_time=helper_data.best_second_publication_time.strftime('%H:%M'),
    ).strip()
    text += '\n\n' + module.footer_text

    await message.reply(
        text=text,
        reply_to_message_id=message.id,
        disable_web_page_preview=True,
        reply_markup=await module.share_keyboard,
    )
