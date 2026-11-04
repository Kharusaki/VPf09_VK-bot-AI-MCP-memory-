"""Точка входа бота: настройка логов, MCP-клиент и LongPoll."""

from __future__ import annotations

import asyncio
import logging

from config.settings import Settings, load_settings
from storage.client.mcp_client import MCPStorageClient
from storage.client.repository import StorageRepository
from utils.errors import StorageError
from utils.logging import configure_logging

from .app import build_app

logger = logging.getLogger(__name__)


async def run_bot(settings: Settings) -> None:
    """Запустить бота до остановки процесса."""
    client = MCPStorageClient(settings.mcp_url, timeout=settings.mcp_timeout)
    storage = StorageRepository(client)
    await client.start()

    try:
        try:
            await storage.ping()
        except StorageError as exc:
            logger.warning(
                "MCP-хранилище пока недоступно (%s): %s. Бот продолжит работу.",
                settings.mcp_url,
                exc,
            )
        else:
            logger.info("MCP-хранилище доступно: %s", settings.mcp_url)

        bot, _ctx = build_app(settings, storage)
        logger.info(
            "Бот запущен. Модель: %s, резервная: %s",
            settings.primary_model,
            settings.fallback_model,
        )
        await bot.run_polling()
    finally:
        await client.stop()


def main() -> None:
    """Синхронная обёртка для запуска из консоли."""
    settings = load_settings()
    configure_logging(settings.log_level, settings.log_file)
    try:
        asyncio.run(run_bot(settings))
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")


__all__ = ("main", "run_bot")
