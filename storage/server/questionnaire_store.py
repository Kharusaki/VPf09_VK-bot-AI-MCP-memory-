"""Отдельное хранилище JSON-анкет для PDF-генератора.

Анкета не является частью профиля пользователя: она лежит в собственном
каталоге и перезаписывается при каждом ходе диалога в режиме
«Анкетирование». Менеджер забирает актуальный JSON и делает из него PDF.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from models.questionnaire import normalize_profile
from utils.locks import KeyedLocks
from utils.time import utc_now

logger = logging.getLogger(__name__)


class QuestionnaireStore:
    """Атомарная запись анкет в data/questionnaires."""

    def __init__(self, directory: Path, max_file_bytes: int = 1_000_000) -> None:
        self.directory = Path(directory).expanduser().resolve()
        self.max_file_bytes = max(10_000, int(max_file_bytes))
        self._locks = KeyedLocks()

    def ensure_ready(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

    def _safe_dialog_id(self, dialog_id: str) -> str:
        safe = "".join(char for char in str(dialog_id) if char.isalnum() or char in "_-")
        return safe[:40] or "dialog"

    def path_for(self, user_id: int, dialog_id: str) -> Path:
        return self.directory / f"anketa_{int(user_id)}_{self._safe_dialog_id(dialog_id)}.json"

    def _save_sync(
        self,
        user_id: int,
        dialog_id: str,
        dialog_title: str,
        display_name: str,
        profile: dict[str, Any],
    ) -> Path:
        path = self.path_for(user_id, dialog_id)
        now = utc_now()

        created_at = now
        if path.exists():
            try:
                with open(path, encoding="utf-8") as file:
                    previous = json.load(file)
                if isinstance(previous, dict) and previous.get("created_at"):
                    created_at = str(previous["created_at"])
            except (OSError, json.JSONDecodeError):
                logger.warning("Не удалось прочитать предыдущую анкету %s", path.name)

        payload: dict[str, Any] = {
            "version": 1,
            "source": "vk_bot",
            "user_id": int(user_id),
            "display_name": display_name,
            "dialog_id": dialog_id,
            "dialog_title": dialog_title,
            "created_at": created_at,
            "updated_at": now,
            **normalize_profile(profile),
        }

        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        if len(encoded) > self.max_file_bytes:
            raise ValueError(f"анкета превышает лимит {self.max_file_bytes} байт")

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

        logger.info("Анкета сохранена: %s", path)
        return path

    async def save(
        self,
        user_id: int,
        dialog_id: str,
        dialog_title: str,
        display_name: str,
        profile: dict[str, Any],
    ) -> Path:
        async with self._locks.get(f"{int(user_id)}:{dialog_id}"):
            return await asyncio.to_thread(
                self._save_sync,
                int(user_id),
                dialog_id,
                dialog_title,
                display_name,
                profile,
            )
