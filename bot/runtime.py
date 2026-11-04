"""Общее состояние приложения, разделяемое обработчиками."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config.settings import Settings
from services.ai_service import AIService
from services.chat_service import ChatService
from services.context_builder import ContextBuilder
from services.dialog_service import DialogService
from services.memory_service import MemoryService
from services.messaging import MessagingService
from services.rag_service import RAGService
from services.retry_store import RetryStore
from storage.client.repository import StorageRepository


@dataclass(slots=True)
class AppContext:
    """Настройки, сервисы и VK API, доступные хендлерам."""

    settings: Settings
    storage: StorageRepository
    dialogs: DialogService
    memory: MemoryService
    context: ContextBuilder
    ai: AIService
    retry: RetryStore
    chat: ChatService
    messaging: MessagingService
    rag: RAGService
    bot: Any = None
    display_names: dict[int, str] = field(default_factory=dict)

    @property
    def api(self) -> Any:
        return self.bot.api if self.bot is not None else None
