"""Тесты моделей и их сериализации в JSON-совместимые словари."""

from __future__ import annotations

from models.dialog import Dialog
from models.enums import MessageRole, Mode
from models.message import ChatMessage
from models.user import UserProfile
from utils.time import utc_now


def _message(role: MessageRole, text: str) -> ChatMessage:
    return ChatMessage(role=role, content=text, timestamp=utc_now())


def test_chat_message_round_trip() -> None:
    message = _message(MessageRole.USER, "Привет")
    restored = ChatMessage.from_dict(message.to_dict())

    assert restored.role is MessageRole.USER
    assert restored.content == "Привет"
    assert restored.timestamp == message.timestamp


def test_dialog_round_trip_keeps_messages_and_mode() -> None:
    dialog = Dialog(
        id="abc123",
        title="Тестовый диалог",
        mode=Mode.QUESTIONNAIRE,
        created_at=utc_now(),
        updated_at=utc_now(),
        messages=[
            _message(MessageRole.USER, "Объясни дроби"),
            _message(MessageRole.ASSISTANT, "Дробь — это часть целого."),
        ],
        previous_mode=Mode.TEACHER,
    )
    restored = Dialog.from_dict(dialog.to_dict())

    assert restored.id == dialog.id
    assert restored.title == dialog.title
    assert restored.mode is Mode.QUESTIONNAIRE
    assert restored.previous_mode is Mode.TEACHER
    assert [message.content for message in restored.messages] == [
        "Объясни дроби",
        "Дробь — это часть целого.",
    ]
    assert restored.message_count == 2


def test_dialog_from_dict_tolerates_broken_fields() -> None:
    dialog = Dialog.from_dict(
        {
            "id": 123,
            "title": "",
            "mode": "unknown",
            "messages": [{"role": "assistant", "content": "ok"}, "not-a-dict"],
        }
    )

    assert dialog.id == "123"
    assert dialog.title == "Диалог"
    assert dialog.mode is Mode.ASSISTANT
    assert dialog.message_count == 1


def test_user_profile_round_trip_nests_settings() -> None:
    dialog = Dialog(
        id="d1",
        title="Диалог 1",
        mode=Mode.FRIEND,
        created_at=utc_now(),
        updated_at=utc_now(),
        messages=[_message(MessageRole.USER, "Как дела?")],
    )
    profile = UserProfile(
        user_id=42,
        display_name="Иван",
        created_at=utc_now(),
        updated_at=utc_now(),
        active_dialog_id="d1",
        dialog_counter=2,
        dialogs=[dialog],
    )

    raw = profile.to_dict()
    assert raw["settings"] == {"active_dialog_id": "d1", "dialog_counter": 2}

    restored = UserProfile.from_dict(raw)
    assert restored.user_id == 42
    assert restored.display_name == "Иван"
    assert restored.active_dialog_id == "d1"
    assert restored.dialog_counter == 2
    assert restored.active_dialog is not None
    assert restored.active_dialog.title == "Диалог 1"
    assert restored.active_dialog.mode is Mode.FRIEND


def test_user_profile_from_dict_falls_back_to_first_dialog() -> None:
    dialog = Dialog(
        id="first",
        title="Первый",
        mode=Mode.ASSISTANT,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    profile = UserProfile.from_dict(
        {
            "user_id": 1,
            "dialogs": [dialog.to_dict()],
            "settings": {},
        }
    )

    assert profile.active_dialog_id == "first"
    assert profile.dialog_counter == 1
    assert profile.active_dialog is not None
    assert profile.active_dialog.id == "first"
