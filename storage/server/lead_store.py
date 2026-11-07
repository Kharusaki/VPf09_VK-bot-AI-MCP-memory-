"""Отдельное хранилище заявок (лидов).

Заявка создаётся, когда клиент в обычном режиме просит записаться. Она
сохраняется отдельным JSON-файлом в data/leads, после чего диалог переходит
в режим «Анкетирование». Заявка не является частью профиля пользователя и не
попадает в историю сообщений.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from utils.locks import KeyedLocks
from utils.time import utc_now

logger = logging.getLogger(__name__)

MESSAGE_LIMIT = 2_000


class LeadStore:
    """Атомарная запись заявок в data/leads."""

    def __init__(self, directory: Path, max_file_bytes: int = 1_000_000) -> None:
        self.directory = Path(directory).expanduser().resolve()
        self.max_file_bytes = max(10_000, int(max_file_bytes))
        self._locks = KeyedLocks()

    def ensure_ready(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, user_id: int) -> Path:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        return self.directory / f"lead_{int(user_id)}_{stamp}.json"

    def _create_sync(
        self,
        user_id: int,
        display_name: str,
        dialog_id: str,
        dialog_title: str,
        message: str,
    ) -> Path:
        path = self.path_for(user_id)
        now = utc_now()
        payload: dict[str, Any] = {
            "version": 1,
            "source": "vk_bot",
            "status": "new",
            "user_id": int(user_id),
            "display_name": display_name,
            "dialog_id": dialog_id,
            "dialog_title": dialog_title,
            "message": message.strip()[:MESSAGE_LIMIT],
            "created_at": now,
            "updated_at": now,
        }

        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        if len(encoded) > self.max_file_bytes:
            raise ValueError(f"заявка превышает лимит {self.max_file_bytes} байт")

        self.ensure_ready()
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with open(temp_path, "wb") as file:
                file.write(encoded)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()

        logger.info("Заявка создана: %s", path)
        return path

    async def create(
        self,
        user_id: int,
        display_name: str,
        dialog_id: str,
        dialog_title: str,
        message: str,
    ) -> Path:
        async with self._locks.get(int(user_id)):
            return await asyncio.to_thread(
                self._create_sync,
                int(user_id),
                display_name,
                dialog_id,
                dialog_title,
                message,
            )


__all__ = ("LeadStore",)
