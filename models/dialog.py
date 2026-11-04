"""Модель диалога."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from utils.time import utc_now

from .enums import Mode
from .message import ChatMessage


@dataclass(slots=True)
class Dialog:
    """Независимый диалог пользователя со своей историей и режимом."""

    id: str
    title: str
    mode: Mode
    created_at: str
    updated_at: str
    messages: list[ChatMessage] = field(default_factory=list)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Dialog:
        raw_messages = data.get("messages")
        messages: list[ChatMessage] = []
        if isinstance(raw_messages, list):
            messages = [
                ChatMessage.from_dict(item)
                for item in raw_messages
                if isinstance(item, Mapping)
            ]
        return cls(
            id=str(data.get("id") or ""),
            title=str(data.get("title") or "Диалог"),
            mode=Mode.from_value(data.get("mode")),
            created_at=str(data.get("created_at") or "") or utc_now(),
            updated_at=str(data.get("updated_at") or "") or utc_now(),
            messages=messages,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "mode": self.mode.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [message.to_dict() for message in self.messages],
        }
