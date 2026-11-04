"""Единый формат времени для JSON-хранилища и сообщений."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> str:
    """Вернуть текущее UTC-время в ISO-формате с секундной точностью."""
    return datetime.now(UTC).isoformat(timespec="seconds")
