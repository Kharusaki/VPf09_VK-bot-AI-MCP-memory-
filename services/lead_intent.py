"""Распознавание намерения оставить заявку в обычном диалоге.

Триггер срабатывает по явным фразам, а не по одиночным словам: «записаться»
или «оставить заявку» означают действие, а простое упоминание «пробного урока»
может быть вопросом о цене. Детектор не обращается к модели и работает
мгновенно, поэтому не добавляет задержку к ответу бота.
"""

from __future__ import annotations

import re

_LEAD_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bзаписаться\b",
        r"\bзапишите меня\b",
        r"\bзапиши меня\b",
        r"\bхочу (учиться|заниматься)\b",
        r"\b(оставить|оставьте|оставь) заявку\b",
        r"\b(создать|создайте|создай) заявку\b",
        r"\b(оформить|оформите|оформи) заявку\b",
        r"\bзаявку на (обучение|занятия|урок)\b",
        r"\bхочу на (пробный урок|пробное занятие)\b",
    )
)


def detect_lead_intent(text: str) -> bool:
    """Похоже ли сообщение на просьбу записаться или оставить заявку."""
    if not text:
        return False
    normalized = text.lower().replace("ё", "е").strip()
    if re.search(r"\bне\s+(хочу\s+)?(записаться|записываться)\b", normalized):
        return False
    if re.search(r"\bне\s+(надо|нужно)\s+заявк", normalized):
        return False
    return any(pattern.search(normalized) for pattern in _LEAD_PATTERNS)


__all__ = ("detect_lead_intent",)
