"""Типизированный доступ бота к MCP-хранилищу.

Сервисы работают с UserProfile и не знают, что за ним стоит HTTP и JSON.
Все ошибки транспорта приводятся к StorageError.
"""

from __future__ import annotations

from typing import Any

from models.user import UserProfile
from utils.errors import StorageError

from .mcp_client import MCPStorageClient


class StorageRepository:
    """Профили пользователей через MCP-инструменты."""

    def __init__(self, client: MCPStorageClient) -> None:
        self.client = client

    async def ping(self) -> dict[str, Any]:
        return await self.client.ping()

    async def stats(self) -> dict[str, Any]:
        return await self.client.call_tool("storage_stats", {})

    async def load_user(self, user_id: int) -> UserProfile | None:
        """Прочитать профиль или вернуть None для нового пользователя."""
        payload = await self.client.call_tool("get_user", {"user_id": int(user_id)})
        if not payload.get("exists"):
            return None
        raw = payload.get("user")
        if not isinstance(raw, dict):
            raise StorageError("Хранилище вернуло профиль неверного формата")
        profile = UserProfile.from_dict(raw)
        profile.user_id = int(user_id)
        return profile

    async def save_user(self, profile: UserProfile) -> None:
        """Полностью сохранить профиль пользователя."""
        await self.client.call_tool(
            "save_user",
            {"user_id": int(profile.user_id), "user": profile.to_dict()},
        )

    async def delete_user(self, user_id: int) -> None:
        await self.client.call_tool("delete_user", {"user_id": int(user_id)})

    async def save_questionnaire(
        self,
        user_id: int,
        dialog_id: str,
        dialog_title: str,
        display_name: str,
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        """Сохранить анкету отдельным JSON-файлом для PDF-генератора."""
        return await self.client.call_tool(
            "save_questionnaire",
            {
                "user_id": int(user_id),
                "dialog_id": str(dialog_id),
                "dialog_title": str(dialog_title),
                "display_name": str(display_name),
                "profile": profile,
            },
        )

    async def list_user_ids(self) -> list[int]:
        payload = await self.client.call_tool("list_users", {})
        raw = payload.get("user_ids")
        if not isinstance(raw, list):
            return []
        result: list[int] = []
        for item in raw:
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                continue
        return result

    async def close(self) -> None:
        await self.client.stop()
