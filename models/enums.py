"""Перечисления предметной области."""

from __future__ import annotations

from enum import StrEnum


class Mode(StrEnum):
    """Режим общения. Значение совпадает с полем mode в JSON."""

    ASSISTANT = "assistant"
    PROGRAMMER = "programmer"
    TEACHER = "teacher"
    BUSINESS = "business"
    FRIEND = "friend"
    RAG = "rag"

    @property
    def label(self) -> str:
        """Подпись кнопки на русском."""
        return _MODE_LABELS[self]

    @classmethod
    def from_value(cls, value: object) -> Mode:
        """Безопасно привести строку к режиму, иначе — обычный помощник."""
        try:
            return cls(str(value))
        except ValueError:
            return cls.ASSISTANT


_MODE_LABELS: dict[Mode, str] = {
    Mode.ASSISTANT: "🤖 Обычный помощник",
    Mode.PROGRAMMER: "👨‍💻 Программист",
    Mode.TEACHER: "🎓 Преподаватель",
    Mode.BUSINESS: "💼 Бизнес-консультант",
    Mode.FRIEND: "😊 Дружелюбный собеседник",
    Mode.RAG: "📚 Менеджер по базе знаний",
}


class MessageRole(StrEnum):
    """Роль автора сообщения в истории."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    @classmethod
    def from_value(cls, value: object) -> MessageRole:
        try:
            return cls(str(value))
        except ValueError:
            return cls.USER