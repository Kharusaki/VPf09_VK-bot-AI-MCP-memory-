"""Сборка контекста для модели.

В контекст попадают только последние сообщения и только в пределах бюджета
символов. Обрезка идёт с конца: свежие реплики важнее старых. Если после
обрезки первым оказался ответ ассистента, он отбрасывается — диалог для
модели должен начинаться с вопроса пользователя.
"""

from __future__ import annotations

from models.dialog import Dialog
from models.enums import MessageRole
from models.message import ChatMessage


class ContextBuilder:
    """Формирует список сообщений для AI-провайдера."""

    def __init__(self, history_limit: int, max_chars: int) -> None:
        self.history_limit = max(2, int(history_limit))
        self.max_chars = max(1000, int(max_chars))

    def build(self, dialog: Dialog) -> list[dict[str, str]]:
        """Вернуть историю в формате role/content."""
        messages = [
            message
            for message in dialog.messages[-self.history_limit :]
            if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
            and message.content.strip()
        ]
        selected = self._fit_budget(messages)

        while selected and selected[0].role is MessageRole.ASSISTANT:
            selected.pop(0)

        return [
            {"role": message.role.value, "content": message.content}
            for message in selected
        ]

    def _fit_budget(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        if not messages:
            return []

        total = 0
        start = len(messages)
        for index in range(len(messages) - 1, -1, -1):
            total += len(messages[index].content)
            if total > self.max_chars and start < len(messages):
                break
            start = index
        return list(messages[start:])
