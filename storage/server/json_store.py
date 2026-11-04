"""Атомарное JSON-хранилище профилей пользователей.

Один пользователь — один файл data/users/{user_id}.json. Запись выполняется
через временный файл и os.replace, поэтому при сбое процесса на диске остаётся
либо старая, либо новая версия, но не «половина» JSON.

Повреждённый файл не удаляется: он переименовывается в *.corrupt-<время>.json,
а пользователь получает чистый профиль. Так данные можно восстановить вручную.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from utils.locks import KeyedLocks

logger = logging.getLogger(__name__)


class JsonUserStore:
    """Файловое хранилище профилей с блокировками по пользователю."""

    def __init__(self, data_dir: Path, max_file_bytes: int = 5_000_000) -> None:
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.max_file_bytes = max(10_000, int(max_file_bytes))
        self._locks = KeyedLocks()

    def ensure_ready(self) -> None:
        """Создать каталог данных при старте сервера."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: int) -> Path:
        return self.data_dir / f"{int(user_id)}.json"

    def _backup_corrupt(self, path: Path) -> None:
        """Сохранить повреждённый файл рядом, не мешая работе пользователя."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
        try:
            os.replace(path, target)
            logger.warning("Повреждённый профиль сохранён как %s", target.name)
        except OSError as exc:
            logger.error("Не удалось сохранить повреждённый профиль %s: %s", path, exc)

    def _read_sync(self, user_id: int) -> dict[str, Any] | None:
        path = self._path(user_id)
        if not path.exists():
            return None
        try:
            size = path.stat().st_size
            if size > self.max_file_bytes:
                raise ValueError(f"файл слишком большой ({size} байт)")
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict):
                raise ValueError("корень JSON должен быть объектом")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Профиль %s повреждён: %s", user_id, exc)
            self._backup_corrupt(path)
            return None
        return data

    def _write_sync(self, user_id: int, data: dict[str, Any]) -> None:
        path = self._path(user_id)
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        encoded = payload.encode("utf-8")
        if len(encoded) > self.max_file_bytes:
            raise ValueError(
                f"профиль превышает лимит {self.max_file_bytes} байт"
            )

        self.data_dir.mkdir(parents=True, exist_ok=True)
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

    async def read(self, user_id: int) -> dict[str, Any] | None:
        """Прочитать профиль или None, если файла нет."""
        async with self._locks.get(int(user_id)):
            return await asyncio.to_thread(self._read_sync, int(user_id))

    async def write(self, user_id: int, data: dict[str, Any]) -> None:
        """Полностью заменить профиль пользователя."""
        async with self._locks.get(int(user_id)):
            await asyncio.to_thread(self._write_sync, int(user_id), data)

    async def delete(self, user_id: int) -> bool:
        """Удалить профиль. Возвращает True, если файл существовал."""
        async with self._locks.get(int(user_id)):
            return await asyncio.to_thread(self._delete_sync, int(user_id))

    def _delete_sync(self, user_id: int) -> bool:
        path = self._path(user_id)
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False

    async def list_users(self) -> list[int]:
        """Список ID пользователей, у которых есть файл профиля."""
        return await asyncio.to_thread(self._list_sync)

    def _list_sync(self) -> list[int]:
        if not self.data_dir.exists():
            return []
        result: list[int] = []
        for path in self.data_dir.glob("*.json"):
            if path.name.startswith(".") or ".corrupt-" in path.name:
                continue
            try:
                result.append(int(path.stem))
            except ValueError:
                continue
        return sorted(result)

    async def stats(self) -> dict[str, Any]:
        """Краткая статистика каталога для health-check."""
        return await asyncio.to_thread(self._stats_sync)

    def _stats_sync(self) -> dict[str, Any]:
        files = [
            path
            for path in self.data_dir.glob("*.json")
            if not path.name.startswith(".") and ".corrupt-" not in path.name
        ] if self.data_dir.exists() else []
        total_bytes = 0
        for path in files:
            try:
                total_bytes += path.stat().st_size
            except OSError:
                continue
        return {
            "data_dir": str(self.data_dir),
            "users": len(files),
            "total_bytes": total_bytes,
        }
