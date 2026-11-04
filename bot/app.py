"""Сборка VK-бота и общего контекста приложения."""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any

from vkbottle import API, Bot, BotPolling, ErrorHandler
from vkbottle.bot import BotLabeler, Message, MessageEvent

from config import texts
from config.settings import Settings
from keyboards.main import main_menu
from services.ai_service import AIService
from services.chat_service import ChatService
from services.context_builder import ContextBuilder
from services.dialog_service import DialogService
from services.memory_service import MemoryService
from services.messaging import MessagingService
from services.retry_store import RetryStore
from storage.client.repository import StorageRepository
from utils.errors import StorageError

from .handlers import register_handlers
from .runtime import AppContext

logger = logging.getLogger(__name__)


def build_app(settings: Settings, storage: StorageRepository) -> tuple[Bot, AppContext]:
    """Создать бота, сервисы и зарегистрировать обработчики."""
    api = API(settings.vk_group_token)
    polling = BotPolling(api=api, group_id=settings.vk_group_id)
    error_handler = ErrorHandler(redirect_arguments=True)
    labeler = BotLabeler(error_handler=error_handler)
    bot = Bot(
        api=api,
        polling=polling,
        labeler=labeler,
        error_handler=error_handler,
    )

    memory = MemoryService(
        limit=settings.history_limit,
        max_chars=settings.history_max_chars,
        max_message_chars=settings.max_message_chars,
    )
    context = ContextBuilder(
        history_limit=settings.history_limit,
        max_chars=settings.history_max_chars,
    )
    dialogs = DialogService(storage=storage, settings=settings)
    ai = AIService(settings=settings)
    chat = ChatService(
        storage=storage,
        dialogs=dialogs,
        memory=memory,
        context=context,
        ai=ai,
        settings=settings,
    )

    ctx = AppContext(
        settings=settings,
        storage=storage,
        dialogs=dialogs,
        memory=memory,
        context=context,
        ai=ai,
        retry=RetryStore(),
        chat=chat,
        messaging=MessagingService(api, settings),
        bot=bot,
    )

    register_handlers(labeler, ctx)
    _register_error_handlers(error_handler, ctx)
    return bot, ctx


def _register_error_handlers(error_handler: ErrorHandler, ctx: AppContext) -> None:
    """Показать пользователю понятный текст вместо трейсбека в логах."""

    @error_handler.register_error_handler(StorageError)
    async def on_storage_error(error: Exception, event: Any = None) -> None:
        logger.error("Ошибка MCP-хранилища: %s", error)
        await _notify(ctx, event, texts.STORAGE_ERROR_TEXT)

    async def on_undefined_error(error: Exception, event: Any = None) -> None:
        logger.error(
            "Необработанная ошибка: %s",
            error,
            exc_info=(type(error), error, error.__traceback__),
        )
        await _notify(ctx, event, texts.NETWORK_ERROR_TEXT)

    error_handler.register_undefined_error_handler(on_undefined_error)


async def _notify(ctx: AppContext, event: Any, text: str) -> None:
    """Аккуратно сообщить об ошибке в сообщение или callback."""
    if isinstance(event, MessageEvent):
        with suppress(Exception):
            await event.show_snackbar(text.split("\n", 1)[0][:90])
        return
    if isinstance(event, Message):
        with suppress(Exception):
            await ctx.messaging.send(int(event.peer_id), text, main_menu())


__all__ = ("build_app",)
