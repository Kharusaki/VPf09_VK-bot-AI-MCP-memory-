"""Точка входа бота: настройка логов, MCP-клиент и LongPoll."""

from __future__ import annotations

import asyncio
import logging

from vkbottle import API
from vkbottle.exception_factory.base_exceptions import VKAPIError

from config.settings import Settings, load_settings
from storage.client.mcp_client import MCPStorageClient
from storage.client.repository import StorageRepository
from utils.errors import StorageError
from utils.logging import configure_logging

from .app import build_app

logger = logging.getLogger(__name__)

_MANAGE_HINT = (
    "Сообщество доступно, но у ключа нет права «Управление сообществом» (manage).\n"
    "Long Poll без него не запустится. Создайте новый ключ:\n"
    "  Управление → Работа с API → Ключи доступа → Создать ключ\n"
    "и обязательно отметьте пункты «Сообщения» И «Управление сообществом»."
)
_NOT_ADMIN_HINT = (
    "Ключ принят, но VK не видит вас администратором сообщества {gid}.\n"
    "Проверьте, что токен создан именно для этого сообщества и у вашего\n"
    "аккаунта есть права администратора или редактора."
)


async def check_vk_token(api: API, group_id: int | None) -> None:
    """Проверить права ключа до запуска Long Poll и объяснить проблему человеком.

    VK на нехватку права отдаёт общий «Access denied» (код 15), из-за которого
    в трейсбеке ничего не понять. Разделяем две частые причины: ключ без
    manage и ключ не от своего сообщества.
    """
    try:
        response = await api.request("groups.getById", {})
    except Exception as exc:
        raise RuntimeError(f"VK отклонил ключ доступа: {exc}") from exc

    groups = response.get("groups") or []
    resolved_id = group_id or (groups[0]["id"] if groups else None)
    if resolved_id is None:
        raise RuntimeError("Не удалось определить ID сообщества. Заполните VK_GROUP_ID в .env.")

    try:
        await api.request("groups.getLongPollServer", {"group_id": resolved_id})
    except VKAPIError as exc:
        if exc.code != 15:
            raise
        # Код 15 общий: не хватает либо права manage, либо прав администратора.
        # groups.getMembers требует ровно manage и ничего больше — по нему и
        # различаем две причины.
        try:
            await api.request("groups.getMembers", {"group_id": resolved_id, "count": 1})
        except VKAPIError:
            raise RuntimeError(_MANAGE_HINT) from exc
        raise RuntimeError(_NOT_ADMIN_HINT.format(gid=resolved_id)) from exc
    except Exception as exc:
        raise RuntimeError(f"VK не отдал сервер Long Poll: {exc}") from exc


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

        await check_vk_token(API(settings.vk_group_token), settings.vk_group_id)
        logger.info("Ключ VK проверен: сообщения и Long Poll доступны")

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
    except RuntimeError as exc:
        logger.error("Бот не запущен: %s", exc)


__all__ = ("check_vk_token", "main", "run_bot")

