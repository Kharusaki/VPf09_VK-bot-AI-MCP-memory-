"""Интеграция режима анкетирования в ChatService."""

from __future__ import annotations

import json
from typing import Any

from models.dialog import Dialog
from models.enums import MessageRole, Mode
from models.user import UserProfile
from services.ai_service import AIResult
from services.chat_service import ChatService
from services.context_builder import ContextBuilder
from services.dialog_service import DialogService
from services.memory_service import MemoryService
from utils.time import utc_now

from .conftest import make_settings

SAMPLE = {
    "student_name": "Артём Соколов",
    "age_or_grade": "11 лет, 5 класс",
    "current_level": "A2",
    "learning_goal": "Разговорный английский",
    "preferred_schedule": "Пн и ср в 16:00",
    "format_preference": "Офлайн, группа",
    "previous_experience": "Школьная программа",
    "special_notes": "Застенчивый",
    "contact_info": "Папа Дмитрий, +7 912 555-11-22",
    "next_steps": "Пробный урок 18 ноября",
}


class FakeStorage:
    def __init__(self, profile: UserProfile) -> None:
        self.profile = profile
        self.questionnaire: dict[str, Any] | None = None

    async def load_user(self, user_id: int) -> UserProfile:
        return self.profile

    async def save_user(self, profile: UserProfile) -> None:
        self.profile = profile

    async def save_questionnaire(self, **kwargs: Any) -> dict[str, Any]:
        self.questionnaire = kwargs
        return {"ok": True, "file": "anketa_1_dialog-1.json"}


class FakeAI:
    def __init__(self, text: str) -> None:
        self.text = text

    async def generate(self, system_prompt: str, messages: list[dict[str, str]]) -> AIResult:
        return AIResult(text=self.text, model="test-model", fallback_used=False)


def _profile(mode: Mode = Mode.QUESTIONNAIRE) -> UserProfile:
    now = utc_now()
    dialog = Dialog(
        id="dialog-1",
        title="Анкета",
        mode=mode,
        created_at=now,
        updated_at=now,
    )
    return UserProfile(
        user_id=1,
        display_name="Тест",
        created_at=now,
        updated_at=now,
        active_dialog_id=dialog.id,
        dialog_counter=2,
        dialogs=[dialog],
    )


def _chat(profile: UserProfile, answer: str) -> tuple[ChatService, FakeStorage]:
    settings = make_settings()
    storage = FakeStorage(profile)
    chat = ChatService(
        storage=storage,  # type: ignore[arg-type]
        dialogs=DialogService(storage=storage, settings=settings),  # type: ignore[arg-type]
        memory=MemoryService(limit=100, max_chars=14_000, max_message_chars=3_800),
        context=ContextBuilder(history_limit=100, max_chars=14_000),
        ai=FakeAI(answer),  # type: ignore[arg-type]
        settings=settings,
    )
    return chat, storage


async def test_questionnaire_json_is_saved_and_hidden() -> None:
    answer = (
        "Отлично, Артём! Предлагаю пробный урок в среду.\n\n"
        "```json\n" + json.dumps(SAMPLE, ensure_ascii=False) + "\n```"
    )
    chat, storage = _chat(_profile(), answer)

    result = await chat.reply(1, "Тест", "Меня зовут Артём")

    assert result.text == "Отлично, Артём! Предлагаю пробный урок в среду."
    assert "json" not in result.text.lower()
    assert storage.questionnaire is not None
    assert storage.questionnaire["dialog_id"] == "dialog-1"
    assert storage.questionnaire["profile"] == SAMPLE
    assert result.questionnaire_file == "anketa_1_dialog-1.json"

    dialog = storage.profile.active_dialog
    assert dialog is not None
    assert [message.content for message in dialog.messages] == [
        "Меня зовут Артём",
        "Отлично, Артём! Предлагаю пробный урок в среду.",
    ]
    assert dialog.messages[-1].role is MessageRole.ASSISTANT


async def test_broken_json_block_is_removed_from_reply() -> None:
    chat, storage = _chat(_profile(), "Привет!\n```json\n{broken}\n```")

    result = await chat.reply(1, "Тест", "Здравствуйте")

    assert result.text == "Привет!"
    assert storage.questionnaire is None


async def test_non_questionnaire_mode_keeps_text_as_is() -> None:
    answer = "Обычный ответ без JSON"
    chat, storage = _chat(_profile(Mode.ASSISTANT), answer)

    result = await chat.reply(1, "Тест", "Привет")

    assert result.text == answer
    assert storage.questionnaire is None
