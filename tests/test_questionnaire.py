"""Тесты разбора анкеты и извлечения JSON из ответа модели."""

from __future__ import annotations

import json
from pathlib import Path

from models.questionnaire import (
    DEFAULT_VALUE,
    PROFILE_KEYS,
    extract_profile,
    looks_like_profile,
    normalize_profile,
    strip_json_blocks,
)
from services.questionnaire_extract import load_source

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


def test_extract_profile_from_fenced_json() -> None:
    text = (
        "Отлично, записал. Предлагаю пробный урок в среду.\n\n"
        "```json\n"
        + json.dumps(SAMPLE, ensure_ascii=False, indent=2)
        + "\n```"
    )

    cleaned, profile = extract_profile(text)

    assert cleaned == "Отлично, записал. Предлагаю пробный урок в среду."
    assert profile == SAMPLE


def test_extract_profile_from_raw_json() -> None:
    text = "Готово: " + json.dumps(SAMPLE, ensure_ascii=False)
    cleaned, profile = extract_profile(text)

    assert cleaned == "Готово:"
    assert profile == SAMPLE


def test_extract_profile_ignores_foreign_json() -> None:
    text = 'Вот пример: {"foo": 1, "bar": 2}'
    cleaned, profile = extract_profile(text)

    assert cleaned == text
    assert profile is None


def test_normalize_fills_missing_fields() -> None:
    profile = normalize_profile({"student_name": "Артём", "learning_goal": " "})

    assert tuple(profile) == PROFILE_KEYS
    assert profile["student_name"] == "Артём"
    assert profile["learning_goal"] == DEFAULT_VALUE
    assert profile["contact_info"] == DEFAULT_VALUE


def test_looks_like_profile_needs_several_fields() -> None:
    assert looks_like_profile(SAMPLE) is True
    assert looks_like_profile({"student_name": "A", "learning_goal": "B"}) is False
    assert looks_like_profile([]) is False


def test_strip_json_blocks_removes_service_block() -> None:
    text = "Реплика\n```json\n{}\n```"
    assert strip_json_blocks(text) == "Реплика"


def test_load_source_accepts_ready_bot_json(tmp_path: Path) -> None:
    path = tmp_path / "anketa.json"
    path.write_text(
        json.dumps({**SAMPLE, "user_id": 1}, ensure_ascii=False),
        encoding="utf-8",
    )

    text, profile = load_source(path)

    assert text == ""
    assert profile == SAMPLE


def test_load_source_converts_message_history(tmp_path: Path) -> None:
    path = tmp_path / "dialog.json"
    path.write_text(
        json.dumps(
            {
                "messages": [
                    {"from": "bot", "text": "Здравствуйте!"},
                    {"from": "user", "text": "Здравствуйте, ищу репетитора."},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    text, profile = load_source(path)

    assert profile is None
    assert text == "Менеджер: Здравствуйте!\nКлиент: Здравствуйте, ищу репетитора."


def test_load_source_reads_plain_text(tmp_path: Path) -> None:
    path = tmp_path / "dialog.txt"
    path.write_text("Менеджер: Привет\nКлиент: Привет", encoding="utf-8")

    text, profile = load_source(path)

    assert profile is None
    assert "Клиент: Привет" in text
