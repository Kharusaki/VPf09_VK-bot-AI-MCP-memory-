"""Модель одного сообщения истории."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from utils.time import utc_now

from .enums import MessageRole


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Сообщение в истории диалога."""

    role: MessageRole
    content: str
    timestamp: str = field(default_factory=utc_now)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ChatMessage:
        return cls(
            role=MessageRole.from_value(data.get("role")),
            content=str(data.get("content") or ""),
            timestamp=str(data.get("timestamp") or "") or utc_now(),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
        }
