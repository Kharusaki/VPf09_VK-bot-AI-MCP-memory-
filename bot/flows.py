"""Сценарии обработки текста: обычный запрос и повтор после ошибки."""

from __future__ import annotations

import logging

from vkbottle.bot import MessageEvent

from config import texts
from keyboards.main import main_menu
from keyboards.retry import retry_keyboard
from utils.errors import AIUnavailableError, StorageError
from utils.text import clean_text, utf16_len

from .runtime import AppContext
from .views import edit_event

logger = logging.getLogger(__name__)


async def process_text(
    ctx: AppContext,
    peer_id: int,
    user_id: int,
    text: str,
    display_name: str = "",
) -> None:
    """Проверить текст, получить ответ AI и показать его пользователю."""
    message = clean_text(text)
    if not message:
        await ctx.messaging.send(peer_id, texts.EMPTY_TEXT, main_menu())
        return

    length = utf16_len(message)
    if length > ctx.settings.max_message_chars:
        await ctx.messaging.send(
            peer_id,
            texts.TOO_LONG_TEXT.format(
                length=length, limit=ctx.settings.max_message_chars
            ),
            main_menu(),
        )
        return

    await ctx.messaging.typing(peer_id)
    placeholder_id = await ctx.messaging.send_placeholder(peer_id)

    try:
        result = await ctx.chat.reply(user_id, display_name, message)
    except AIUnavailableError:
        ctx.retry.put(user_id, message)
        await ctx.messaging.replace_placeholder(
            peer_id, placeholder_id, texts.AI_ERROR_TEXT, retry_keyboard()
        )
    except StorageError as exc:
        logger.error("Хранилище недоступно при запросе %s: %s", user_id, exc)
        await ctx.messaging.replace_placeholder(
            peer_id, placeholder_id, texts.STORAGE_ERROR_TEXT, main_menu()
        )
    except Exception as exc:
        logger.exception("Неожиданная ошибка при запросе %s: %s", user_id, exc)
        ctx.retry.put(user_id, message)
        await ctx.messaging.replace_placeholder(
            peer_id, placeholder_id, texts.AI_ERROR_TEXT, retry_keyboard()
        )
    else:
        ctx.retry.clear(user_id)
        await ctx.messaging.replace_placeholder(
            peer_id, placeholder_id, result.text, main_menu()
        )


async def retry_last(ctx: AppContext, event: MessageEvent) -> None:
    """Повторить последний неудачный запрос пользователя."""
    text = ctx.retry.pop(int(event.user_id))
    if not text:
        await event.show_snackbar(texts.RETRY_NOT_FOUND_TEXT)
        return

    await edit_event(event, "🔁 Повторяю запрос…")
    await process_text(ctx, int(event.peer_id), int(event.user_id), text)
