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
from config.texts import (
    LEAD_CREATED_TEXT,
    QUESTIONNAIRE_SAVE_ERROR_TEXT,
    QUESTIONNAIRE_SAVED_TEXT,
    questionnaire_completed_text,
)
from models.dialog import Dialog
from models.enums import MessageRole, Mode
from models.questionnaire import (
    extract_profile,
    is_profile_complete,
    strip_json_blocks,
)
from models.user import UserProfile
from services.ai_service import AIService
from services.context_builder import ContextBuilder
from services.dialog_service import DialogService
from services.lead_intent import detect_lead_intent
from services.memory_service import MemoryService
from services.rag_service import RAGService
from storage.client.repository import StorageRepository
from utils.errors import AIUnavailableError, StorageError
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
    questionnaire_file: str | None = None


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

            lead_created = False
            if dialog.mode is not Mode.QUESTIONNAIRE and detect_lead_intent(message):
                lead_created = await self._start_questionnaire(
                    profile, dialog, user_id, display_name, message
                )

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

            visible_text = result.text
            questionnaire_file: str | None = None
            returned_mode: Mode | None = None
            if dialog.mode is Mode.QUESTIONNAIRE:
                visible_text, questionnaire = extract_profile(result.text)
                if questionnaire is not None:
                    try:
                        saved = await self.storage.save_questionnaire(
                            user_id=int(user_id),
                            dialog_id=dialog.id,
                            dialog_title=dialog.title,
                            display_name=display_name,
                            profile=questionnaire,
                        )
                        questionnaire_file = str(saved.get("file") or "")
                        visible_text = visible_text or QUESTIONNAIRE_SAVED_TEXT
                        if (
                            questionnaire_file
                            and dialog.previous_mode is not None
                            and is_profile_complete(questionnaire)
                        ):
                            returned_mode = dialog.previous_mode
                            self.dialogs.set_mode(
                                profile, returned_mode, dialog.id
                            )
                    except StorageError as exc:
                        logger.error(
                            "Не удалось сохранить анкету пользователя %s: %s",
                            user_id,
                            exc,
                        )
                        visible_text = visible_text or QUESTIONNAIRE_SAVE_ERROR_TEXT
                else:
                    # Модель иногда забывает обёртку или формат. Не показываем
                    # пользователю сырой служебный блок в любом случае.
                    visible_text = strip_json_blocks(result.text) or result.text

            if lead_created:
                visible_text = f"{LEAD_CREATED_TEXT}\n\n{visible_text}".strip()
            if returned_mode is not None:
                visible_text = (
                    f"{visible_text}\n\n"
                    f"{questionnaire_completed_text(returned_mode.label)}"
                ).strip()

            self.memory.append(dialog, MessageRole.ASSISTANT, visible_text)
            await self.dialogs.save(profile)

            logger.info(
                "Ответ для %s: диалог «%s», модель %s%s",
                user_id,
                dialog.title,
                result.model,
                " (резервная)" if result.fallback_used else "",
            )
            if questionnaire_file:
                logger.info("JSON анкеты обновлён: %s", questionnaire_file)
            return ChatResult(
                text=visible_text,
                dialog_id=dialog.id,
                dialog_title=dialog.title,
                mode=dialog.mode,
                model=result.model,
                fallback_used=result.fallback_used,
                message_count=dialog.message_count,
                questionnaire_file=questionnaire_file,
            )

    async def _start_questionnaire(
        self,
        profile: UserProfile,
        dialog: Dialog,
        user_id: int,
        display_name: str,
        message: str,
    ) -> bool:
        """Создать заявку и переключить диалог в режим анкетирования."""
        lead_created = False
        try:
            saved = await self.storage.create_lead(
                user_id=int(user_id),
                display_name=display_name,
                dialog_id=dialog.id,
                dialog_title=dialog.title,
                message=message,
            )
            lead_created = True
            logger.info(
                "Заявка пользователя %s создана: %s",
                user_id,
                saved.get("file") or saved.get("path") or "",
            )
        except StorageError as exc:
            logger.error(
                "Не удалось создать заявку пользователя %s: %s",
                user_id,
                exc,
            )
        self.dialogs.set_mode(profile, Mode.QUESTIONNAIRE, dialog.id)
        # Режим и заявка сохраняются сразу: если AI в этом ходе упадёт,
        # повторный запрос не создаст дубликат заявки.
        await self.dialogs.save(profile)
        return lead_created


def _format_rag_context(chunks) -> str:
    """Собрать найденные чанки в блок для системного промпта."""
    if not chunks:
        return ""
    parts = [
        f"[{index}] ({chunk.source})\n{chunk.text}"
        for index, chunk in enumerate(chunks, start=1)
    ]
    return "\n\n".join(parts)
