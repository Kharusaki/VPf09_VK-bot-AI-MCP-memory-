"""Доменный слой поверх JSON-файлов.

Репозиторий проверяет базовую структуру профиля и не даёт записать мусор,
но не занимается бизнес-логикой: лимиты диалогов и режимы живут в сервисах
бота. Так хранилище остаётся универсальным и легко тестируется.
"""

from __future__ import annotations

from typing import Any

from utils.time import utc_now

from .json_store import JsonUserStore


class UserRepository:
    """Чтение и запись профилей пользователей."""

    def __init__(self, store: JsonUserStore) -> None:
        self.store = store

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        """Вернуть профиль пользователя или None."""
        data = await self.store.read(int(user_id))
        if data is None:
            return None
        if data.get("user_id") != int(user_id):
            # Файл мог быть скопирован вручную. Исправляем идентификатор,
            # чтобы дальнейшие операции не писали чужой профиль.
            data["user_id"] = int(user_id)
        return data

    async def save_user(self, user_id: int, user: dict[str, Any]) -> dict[str, Any]:
        """Проверить и атомарно сохранить профиль."""
        if not isinstance(user, dict):
            raise ValueError("Профиль должен быть JSON-объектом")

        dialogs = user.get("dialogs")
        if dialogs is not None and not isinstance(dialogs, list):
            raise ValueError("Поле dialogs должно быть массивом")

        payload = dict(user)
        payload["version"] = int(payload.get("version") or 1)
        payload["user_id"] = int(user_id)
        payload["updated_at"] = utc_now()
        payload.setdefault("created_at", payload["updated_at"])
        payload.setdefault("display_name", "")

        # active_dialog_id и dialog_counter хранятся внутри settings, но старые
        # профили могли иметь их на верхнем уровне. Поддерживаем оба варианта.
        settings = payload.get("settings")
        settings = dict(settings) if isinstance(settings, dict) else {}
        settings.setdefault(
            "active_dialog_id", str(payload.get("active_dialog_id") or "")
        )
        try:
            counter = int(settings.get("dialog_counter") or payload.get("dialog_counter") or 1)
        except (TypeError, ValueError):
            counter = 1
        settings["dialog_counter"] = max(1, counter)
        payload["settings"] = settings
        payload["active_dialog_id"] = str(settings["active_dialog_id"])
        payload["dialog_counter"] = settings["dialog_counter"]
        payload["dialogs"] = dialogs or []

        await self.store.write(int(user_id), payload)
        return {"ok": True, "user_id": int(user_id), "updated_at": payload["updated_at"]}

    async def delete_user(self, user_id: int) -> dict[str, Any]:
        """Удалить профиль пользователя."""
        removed = await self.store.delete(int(user_id))
        return {"ok": True, "user_id": int(user_id), "removed": removed}

    async def list_users(self) -> list[int]:
        """ID всех пользователей с сохранённым профилем."""
        return await self.store.list_users()

    async def stats(self) -> dict[str, Any]:
        """Статистика хранилища для проверки соединения."""
        data = await self.store.stats()
        return {"ok": True, **data}
