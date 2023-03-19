from pyrogram.enums import ParseMode
from pyrogram.types import Message

from common.models import MessagePreferences  # type: ignore


async def copy_message_with_preferences(source_message: Message, preferences: MessagePreferences,
                                        reply_markup: list) -> Message:
    """
    Bot can't edit user's messages, so a copy of source_message is edited instead.

    message.copy() doesn't preserve .web_page, or to be more specific, original
    message doesn't content .web_page for some reason.
    Seems like .web_page is deprecated.
    """
    _common_params = dict(
        parse_mode=ParseMode.MARKDOWN if preferences.markdown else ParseMode.DISABLED,
        reply_markup=reply_markup,
    )

    if source_message.media or source_message.poll:
        _common_params.update(dict(chat_id=source_message.chat.id))
        if not source_message.poll and source_message.caption:
            _common_params.update(dict(caption=source_message.caption.markdown))
        return await source_message.copy(**_common_params)
    else:
        _common_params.update(dict(
            disable_web_page_preview=not preferences.link_preview,
            text=source_message.text.markdown,
        ))
        return await source_message.reply(**_common_params)
