"""Анкета ученика: схема полей и разбор служебного JSON.

В режиме «Анкетирование» модель возвращает два блока: обычную реплику для
клиента и служебный JSON с текущими данными анкеты. JSON не должен попадать
ни в историю диалога, ни в сообщение пользователю — он сохраняется отдельным
файлом для последующей генерации PDF.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

DEFAULT_VALUE = "не указано"

# Ключ → подпись в PDF. Порядок важен: так поля идут в анкете.
PROFILE_FIELDS: dict[str, str] = {
    "student_name": "Имя ученика",
    "age_or_grade": "Возраст / класс",
    "current_level": "Текущий уровень английского",
    "learning_goal": "Цель обучения",
    "preferred_schedule": "Удобное расписание",
    "format_preference": "Предпочитаемый формат",
    "previous_experience": "Предыдущий опыт",
    "special_notes": "Особые пожелания",
    "contact_info": "Контакты",
    "next_steps": "Следующие шаги",
}

PROFILE_KEYS = tuple(PROFILE_FIELDS)

_FENCED_JSON = re.compile(r"```(?:json)?[ \t]*\r?\n?(.*?)```", re.IGNORECASE | re.DOTALL)


def normalize_profile(data: Mapping[str, Any]) -> dict[str, str]:
    """Привести анкету к схеме: только строки, пропуски — «не указано»."""
    result: dict[str, str] = {}
    for key in PROFILE_KEYS:
        value = data.get(key)
        if value is None:
            value = DEFAULT_VALUE
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        text = str(value).strip()
        result[key] = text or DEFAULT_VALUE
    return result


def looks_like_profile(data: Any) -> bool:
    """Похож ли JSON на анкету, а не на случайный объект из ответа."""
    if not isinstance(data, Mapping):
        return False
    return sum(1 for key in PROFILE_KEYS if key in data) >= 3


def extract_profile(text: str) -> tuple[str, dict[str, str] | None]:
    """Отделить служебный JSON от текста ответа.

    Возвращает очищенный текст и нормализованную анкету. Если JSON не найден
    или он не похож на анкету, текст возвращается без изменений.
    """
    if not text:
        return text, None

    candidates: list[tuple[str, int, int]] = []

    for match in _FENCED_JSON.finditer(text):
        candidates.append((match.group(1), match.start(), match.end()))

    # На случай, если модель забыла markdown-обёртку.
    decoder = json.JSONDecoder()
    position = 0
    while True:
        start = text.find("{", position)
        if start == -1:
            break
        try:
            data, length = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            position = start + 1
            continue
        if looks_like_profile(data):
            candidates.append((text[start : start + length], start, start + length))
        position = start + length

    for raw_json, start, end in candidates:
        try:
            data = json.loads(raw_json.strip())
        except json.JSONDecodeError:
            continue
        if not looks_like_profile(data):
            continue
        cleaned = (text[:start] + text[end:]).strip()
        return cleaned, normalize_profile(data)

    return text, None


def strip_json_blocks(text: str) -> str:
    """Убрать служебные markdown-JSON блоки, если разобрать их не удалось."""
    return _FENCED_JSON.sub("", text).strip()


__all__ = (
    "DEFAULT_VALUE",
    "PROFILE_FIELDS",
    "PROFILE_KEYS",
    "extract_profile",
    "looks_like_profile",
    "normalize_profile",
    "strip_json_blocks",
)
