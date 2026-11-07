"""MCP-инструменты хранилища профилей.

Каждый инструмент возвращает JSON-объект с полем ok. Ошибки валидации не
превращаются в исключения транспорта: клиент получает понятное сообщение и
может показать пользователю текст, не разрывая MCP-сессию.
"""

from __future__ import annotations

import logging
from typing import Any

from .app import mcp, questionnaire_store, repository

logger = logging.getLogger(__name__)


@mcp.tool()
async def ping() -> dict[str, Any]:
    """Проверить, что MCP-сервер хранилища отвечает."""
    return {"ok": True, "service": "vk-assistant-storage"}


@mcp.tool()
async def get_user(user_id: int) -> dict[str, Any]:
    """Прочитать профиль пользователя по его VK ID."""
    try:
        user = await repository.get_user(int(user_id))
    except Exception as exc:
        logger.exception("Не удалось прочитать профиль %s", user_id)
        return {"ok": False, "error": f"Не удалось прочитать профиль: {exc}"}
    return {"ok": True, "exists": user is not None, "user": user}


@mcp.tool()
async def save_user(user_id: int, user: dict[str, Any]) -> dict[str, Any]:
    """Полностью сохранить профиль пользователя (диалоги и настройки)."""
    try:
        return await repository.save_user(int(user_id), user)
    except (ValueError, TypeError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        logger.exception("Не удалось сохранить профиль %s", user_id)
        return {"ok": False, "error": f"Не удалось сохранить профиль: {exc}"}


@mcp.tool()
async def delete_user(user_id: int) -> dict[str, Any]:
    """Удалить профиль пользователя и всю его историю."""
    try:
        return await repository.delete_user(int(user_id))
    except Exception as exc:
        logger.exception("Не удалось удалить профиль %s", user_id)
        return {"ok": False, "error": f"Не удалось удалить профиль: {exc}"}


@mcp.tool()
async def list_users() -> dict[str, Any]:
    """Вернуть ID пользователей, у которых есть сохранённый профиль."""
    try:
        user_ids = await repository.list_users()
    except Exception as exc:
        logger.exception("Не удалось получить список пользователей")
        return {"ok": False, "error": f"Не удалось получить список: {exc}"}
    return {"ok": True, "user_ids": user_ids, "count": len(user_ids)}


@mcp.tool()
async def storage_stats() -> dict[str, Any]:
    """Показать статистику каталога с JSON-профилями."""
    try:
        return await repository.stats()
    except Exception as exc:
        logger.exception("Не удалось получить статистику хранилища")
        return {"ok": False, "error": f"Не удалось получить статистику: {exc}"}


@mcp.tool()
async def save_questionnaire(
    user_id: int,
    dialog_id: str,
    dialog_title: str,
    display_name: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Сохранить JSON-анкету отдельно от профиля и истории диалога."""
    try:
        path = await questionnaire_store.save(
            user_id=int(user_id),
            dialog_id=str(dialog_id),
            dialog_title=str(dialog_title),
            display_name=str(display_name),
            profile=profile,
        )
    except (ValueError, TypeError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        logger.exception("Не удалось сохранить анкету пользователя %s", user_id)
        return {"ok": False, "error": f"Не удалось сохранить анкету: {exc}"}
    return {"ok": True, "path": str(path), "file": path.name}
