"""Память о последнем неудачном запросе для кнопки «Повторить»."""

from __future__ import annotations


class RetryStore:
    """Хранит текст последнего неотправленного запроса по пользователю."""

    def __init__(self) -> None:
        self._items: dict[int, str] = {}

    def put(self, user_id: int, text: str) -> None:
        text = text.strip()
        if text:
            self._items[int(user_id)] = text

    def pop(self, user_id: int) -> str | None:
        return self._items.pop(int(user_id), None)

    def clear(self, user_id: int) -> None:
        self._items.pop(int(user_id), None)
