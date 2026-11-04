"""Оркестрация одного хода диалога.

Сервис связывает хранилище, память, контекст и AI. Обмен сохраняется только
после успешного ответа модели: если AI недоступен, вопрос пользователя не
попадает в историю и диалог остаётся согласованным.

Одновременные сообщения одного пользователя сериализуются блокировкой,
поэтому два быстрых запроса не перезапишут историю друг друга.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.prompts import build_system_prompt
from config.settings import Settings
from models.enums import MessageRole, Mode
from services.ai_service import AIService
from services.context_builder import ContextBuilder
from services.dialog_service import DialogService
from services.memory_service import MemoryService
from services.rag_service import RAGService
from storage.client.repository import StorageRepository
from utils.errors import AIUnavailableError
from utils.locks import KeyedLocks
from utils.text import clean_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChatResult:
    """Готовый ответ и состояние диалога после хода."""

    text: str
    dialog_id: str
    dialog_title: str
    mode: Mode
    model: str
    fallback_used: bool
    message_count: int


class ChatService:
    """Обработка текстового сообщения пользователя."""


    def __init__(
        self,
        storage: StorageRepository,
        dialogs: DialogService,
        memory: MemoryService,
        context: ContextBuilder,
        ai: AIService,
        settings: Settings,
        rag: RAGService | None = None,
    ) -> None:
        self.storage = storage
        self.dialogs = dialogs
        self.memory = memory
        self.context = context
        self.ai = ai
        self.settings = settings
        self.rag = rag
        self._locks = KeyedLocks()

    async def reply(
        self,
        user_id: int,
        display_name: str,
        text: str,
    ) -> ChatResult:
        """Сформировать ответ с учётом истории и режима активного диалога."""
        message = clean_text(text)
        if not message:
            raise ValueError("Пустое сообщение")

        async with self._locks.get(int(user_id)):
            profile = await self.dialogs.get_profile(user_id, display_name)
            dialog = profile.active_dialog
            if dialog is None:
                raise ValueError("У пользователя нет активного диалога")

            self.memory.append(dialog, MessageRole.USER, message)
            context = self.context.build(dialog)
            if not context:
                raise AIUnavailableError("Не удалось собрать контекст диалога")

            rag_context = ""
            if dialog.mode is Mode.RAG and self.rag is not None and self.rag.chunk_count:
                found = await self.rag.search(message, top_k=self.settings.rag_top_k)
                rag_context = _format_rag_context(found)

            result = await self.ai.generate(
                system_prompt=build_system_prompt(dialog.mode, rag_context),
                messages=context,
            )

            self.memory.append(dialog, MessageRole.ASSISTANT, result.text)
            await self.dialogs.save(profile)

            logger.info(
                "Ответ для %s: диалог «%s», модель %s%s",
                user_id,
                dialog.title,
                result.model,
                " (резервная)" if result.fallback_used else "",
            )
            return ChatResult(
                text=result.text,
                dialog_id=dialog.id,
                dialog_title=dialog.title,
                mode=dialog.mode,
                model=result.model,
                fallback_used=result.fallback_used,
                message_count=dialog.message_count,
            )


def _format_rag_context(chunks) -> str:
    """Собрать найденные чанки в блок для системного промпта."""
    if not chunks:
        return ""
    parts = [
        f"[{index}] ({chunk.source})\n{chunk.text}"
        for index, chunk in enumerate(chunks, start=1)
    ]
    return "\n\n".join(parts)
