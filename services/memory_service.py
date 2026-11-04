"""Краткосрочная память диалога.

История ограничена и по количеству сообщений, и по суммарному размеру.
Обрезка выполняется после каждого ответа, поэтому в JSON не накапливаются
гигантские диалоги, а модель не получает лишние токены.
"""

from __future__ import annotations

from models.dialog import Dialog
from models.enums import MessageRole
from models.message import ChatMessage
from utils.text import clean_text, truncate_utf16
from utils.time import utc_now


class MemoryService:
    """Добавление сообщений и обрезка истории под лимиты."""

    def __init__(self, limit: int, max_chars: int, max_message_chars: int) -> None:
        self.limit = max(2, int(limit))
        self.max_chars = max(1000, int(max_chars))
        self.max_message_chars = max(500, int(max_message_chars))

    def append(
        self,
        dialog: Dialog,
        role: MessageRole,
        content: str,
    ) -> ChatMessage | None:
        """Добавить сообщение в историю и обрезать её."""
        text = truncate_utf16(clean_text(content), self.max_message_chars).strip()
        if not text:
            return None
        message = ChatMessage(role=role, content=text, timestamp=utc_now())
        dialog.messages.append(message)
        dialog.updated_at = message.timestamp
        self.trim(dialog)
        return message

    def trim(self, dialog: Dialog) -> None:
        """Уложиться в лимиты по количеству и суммарной длине."""
        messages = dialog.messages
        if len(messages) > self.limit:
            dialog.messages = messages[-self.limit :]
            messages = dialog.messages

        total = sum(len(message.content) for message in messages)
        while len(messages) > 2 and total > self.max_chars:
            removed = messages.pop(0)
            total -= len(removed.content)

    def recent(self, dialog: Dialog) -> list[ChatMessage]:
        """Последние сообщения в пределах лимита."""
        return dialog.messages[-self.limit :]
