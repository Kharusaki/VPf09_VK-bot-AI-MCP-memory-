"""Тесты распознавания намерения оставить заявку."""

from __future__ import annotations

import pytest

from services.lead_intent import detect_lead_intent


@pytest.mark.parametrize(
    "text",
    [
        "Хочу записаться на пробный урок",
        "Как можно записаться к вам?",
        "Запишите меня, пожалуйста",
        "Хочу оставить заявку на обучение",
        "Создай заявку, я готов начать",
        "Помогите оформить заявку",
        "Хочу учиться английскому",
    ],
)
def test_detects_lead_intent(text: str) -> None:
    assert detect_lead_intent(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "Сколько стоит пробный урок?",
        "Расскажи про формат занятий",
        "Не хочу записываться, просто спросил",
        "Не надо заявку, спасибо",
        "Как записать ребёнка в школу в другом городе?",
        "",
    ],
)
def test_ignores_plain_questions(text: str) -> None:
    assert detect_lead_intent(text) is False
