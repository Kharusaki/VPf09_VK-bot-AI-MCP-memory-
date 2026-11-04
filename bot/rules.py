"""Пользовательские правила маршрутизации сообщений."""

from __future__ import annotations

from vkbottle.bot import Message
from vkbottle.dispatch.rules.base import FuncRule


def text_in(*labels: str) -> FuncRule:
    """Совпадение текста с одной из подписей без учёта регистра и пробелов."""
    normalized = {label.strip().casefold() for label in labels}

    def check(message: Message) -> bool:
        return (message.text or "").strip().casefold() in normalized

    return FuncRule(check)
