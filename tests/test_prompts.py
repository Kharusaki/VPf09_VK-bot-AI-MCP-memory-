"""Тесты системных промптов и перечислений."""

from __future__ import annotations

import pytest

from config.prompts import GLOBAL_RULES, build_system_prompt
from models.enums import MessageRole, Mode


@pytest.mark.parametrize("mode", list(Mode))
def test_prompt_contains_global_rules_and_mode_text(mode: Mode) -> None:
    prompt = build_system_prompt(mode)

    assert GLOBAL_RULES in prompt
    assert "ОБЩИЕ ПРАВИЛА" in prompt
    assert len(prompt) > len(GLOBAL_RULES)
    assert "ВКонтакте" in prompt or "VK" in prompt


def test_each_mode_has_unique_prompt() -> None:
    prompts = {mode: build_system_prompt(mode) for mode in Mode}
    assert len(set(prompts.values())) == len(Mode)


def test_mode_from_value_falls_back_to_assistant() -> None:
    assert Mode.from_value("programmer") is Mode.PROGRAMMER
    assert Mode.from_value("unknown") is Mode.ASSISTANT
    assert Mode.from_value(None) is Mode.ASSISTANT


def test_mode_labels_are_russian_and_short() -> None:
    for mode in Mode:
        assert mode.label
        assert len(mode.label) <= 40


def test_message_role_from_value() -> None:
    assert MessageRole.from_value("user") is MessageRole.USER
    assert MessageRole.from_value("assistant") is MessageRole.ASSISTANT
    assert MessageRole.from_value("system") is MessageRole.SYSTEM
    assert MessageRole.from_value("unknown") is MessageRole.USER
