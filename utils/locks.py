"""Блокировки по ключу.

Один пользователь — один активный AI-запрос. Без блокировки два быстрых
сообщения могли бы одновременно прочитать историю и записать ответы в
неверном порядке.
"""

from __future__ import annotations

import asyncio
from typing import Any


class KeyedLocks:
    """Лениво создаваемые asyncio.Lock по произвольному ключу."""

    def __init__(self) -> None:
        self._locks: dict[Any, asyncio.Lock] = {}

    def get(self, key: Any) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock
