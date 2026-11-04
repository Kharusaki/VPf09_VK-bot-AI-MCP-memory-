"""Тесты сборки контекста и краткосрочной памяти."""

from __future__ import annotations

from models.dialog import Dialog
from models.enums import MessageRole, Mode
from models.message import ChatMessage
from services.context_builder import ContextBuilder
from services.memory_service import MemoryService
from utils.time import utc_now


def _dialog(*messages: tuple[MessageRole, str]) -> Dialog:
    now = utc_now()
    return Dialog(
        id="d1",
        title="Диалог",
        mode=Mode.ASSISTANT,
        created_at=now,
        updated_at=now,
        messages=[
            ChatMessage(role=role, content=text, timestamp=now)
            for role, text in messages
        ],
    )


def test_context_returns_messages_in_order() -> None:
    dialog = _dialog(
        (MessageRole.USER, "Первый вопрос"),
        (MessageRole.ASSISTANT, "Первый ответ"),
        (MessageRole.USER, "Второй вопрос"),
    )
    context = ContextBuilder(history_limit=100, max_chars=14_000).build(dialog)

    assert context == [
        {"role": "user", "content": "Первый вопрос"},
        {"role": "assistant", "content": "Первый ответ"},
        {"role": "user", "content": "Второй вопрос"},
    ]


def test_context_drops_leading_assistant_message() -> None:
    dialog = _dialog(
        (MessageRole.ASSISTANT, "Старый ответ"),
        (MessageRole.USER, "Вопрос"),
        (MessageRole.ASSISTANT, "Ответ"),
    )
    context = ContextBuilder(history_limit=100, max_chars=14_000).build(dialog)

    assert context[0] == {"role": "user", "content": "Вопрос"}
    assert len(context) == 2


def test_context_respects_history_limit() -> None:
    dialog = _dialog(
        (MessageRole.USER, "1"),
        (MessageRole.ASSISTANT, "2"),
        (MessageRole.USER, "3"),
        (MessageRole.ASSISTANT, "4"),
    )
    context = ContextBuilder(history_limit=2, max_chars=14_000).build(dialog)

    assert context == [
        {"role": "user", "content": "3"},
        {"role": "assistant", "content": "4"},
    ]


def test_context_skips_empty_messages() -> None:
    dialog = _dialog(
        (MessageRole.USER, "Вопрос"),
        (MessageRole.ASSISTANT, "   "),
        (MessageRole.USER, "Ещё вопрос"),
    )
    context = ContextBuilder(history_limit=100, max_chars=14_000).build(dialog)

    assert context == [
        {"role": "user", "content": "Вопрос"},
        {"role": "user", "content": "Ещё вопрос"},
    ]


def test_context_fits_character_budget_from_the_end() -> None:
    dialog = _dialog(
        (MessageRole.USER, "a" * 400),
        (MessageRole.ASSISTANT, "b" * 400),
        (MessageRole.USER, "c" * 400),
        (MessageRole.ASSISTANT, "d" * 400),
    )
    context = ContextBuilder(history_limit=100, max_chars=1_000).build(dialog)

    assert context == [
        {"role": "user", "content": "c" * 400},
        {"role": "assistant", "content": "d" * 400},
    ]


def test_context_keeps_latest_message_even_if_it_exceeds_budget() -> None:
    dialog = _dialog((MessageRole.USER, "x" * 1_500))
    context = ContextBuilder(history_limit=100, max_chars=1_000).build(dialog)

    assert context == [{"role": "user", "content": "x" * 1_500}]


def test_memory_trims_by_count() -> None:
    dialog = _dialog()
    memory = MemoryService(limit=4, max_chars=10_000, max_message_chars=3_800)

    for index in range(6):
        memory.append(dialog, MessageRole.USER, f"Сообщение {index}")

    assert dialog.message_count == 4
    assert [message.content for message in dialog.messages] == [
        "Сообщение 2",
        "Сообщение 3",
        "Сообщение 4",
        "Сообщение 5",
    ]


def test_memory_trims_by_total_size_but_keeps_two_messages() -> None:
    dialog = _dialog()
    memory = MemoryService(limit=100, max_chars=1_000, max_message_chars=3_800)

    for _ in range(10):
        memory.append(dialog, MessageRole.USER, "y" * 300)

    assert dialog.message_count >= 2
    assert sum(len(message.content) for message in dialog.messages) <= 1_000 or dialog.message_count == 2


def test_memory_ignores_empty_content_and_updates_timestamp() -> None:
    dialog = _dialog()
    memory = MemoryService(limit=10, max_chars=10_000, max_message_chars=3_800)

    assert memory.append(dialog, MessageRole.USER, "   ") is None
    assert dialog.message_count == 0

    old_updated = dialog.updated_at
    message = memory.append(dialog, MessageRole.USER, "Привет")
    assert message is not None
    assert dialog.updated_at == message.timestamp
    assert dialog.updated_at != "" and old_updated != ""


def test_memory_truncates_too_long_message() -> None:
    dialog = _dialog()
    memory = MemoryService(limit=10, max_chars=10_000, max_message_chars=500)

    message = memory.append(dialog, MessageRole.USER, "z" * 2_000)

    assert message is not None
    assert len(message.content) == 500
