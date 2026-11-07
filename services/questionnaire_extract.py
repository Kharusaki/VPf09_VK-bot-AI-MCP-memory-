"""Загрузка входных файлов и AI-извлечение анкеты для CLI.

Поддерживаются три вида входа:
- готовый JSON бота (поля анкеты уже на верхнем уровне);
- JSON с историей сообщений (`{"messages": [...]}`);
- обычный текст или транскрибация диалога.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from models.questionnaire import (
    DEFAULT_VALUE,
    PROFILE_FIELDS,
    extract_profile,
    looks_like_profile,
    normalize_profile,
)
from services.ai_service import AIService
from services.profile_pdf import PROJECT_ROOT

logger = logging.getLogger(__name__)


def _looks_like_json(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def json_to_dialog_text(data: Mapping[str, Any]) -> str:
    """Превратить JSON с сообщениями в текст «Роль: реплика»."""
    raw_messages = data.get("messages", [])
    if not isinstance(raw_messages, list):
        return json.dumps(data, ensure_ascii=False, indent=2)

    lines: list[str] = []
    for item in raw_messages:
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("from") or item.get("role") or "unknown")
        role_ru = {
            "bot": "Менеджер",
            "assistant": "Менеджер",
            "user": "Клиент",
            "client": "Клиент",
        }.get(role, role)
        text = str(item.get("text") or item.get("content") or "").strip()
        if text:
            lines.append(f"{role_ru}: {text}")
    return "\n".join(lines)


def load_source(path: Path) -> tuple[str, dict[str, str] | None]:
    """Прочитать файл. Если это готовая анкета — вернуть её сразу."""
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() != ".json" and not _looks_like_json(raw):
        return raw, None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("%s похож на JSON, но не парсится. Читаю как текст.", path.name)
        return raw, None

    if looks_like_profile(data):
        return "", normalize_profile(data)

    if isinstance(data, Mapping):
        return json_to_dialog_text(data), None
    return raw, None


def build_extraction_prompt(dialog_text: str) -> str:
    """Промпт для извлечения анкеты из сырого диалога."""
    fields = "\n".join(
        f'- "{key}" — {label}' for key, label in PROFILE_FIELDS.items()
    )
    return f"""Ты — ассистент школы английского языка.
Извлеки из диалога данные для анкеты ученика.

Схема JSON (все значения — строки):
{fields}

Правила:
1. Верни СТРОГО JSON-объект без markdown-обёрток и пояснений.
2. Если информации нет — поставь строку "{DEFAULT_VALUE}".
3. Не выдумывай факты, которых нет в диалоге.
4. Вход может быть текстом, транскрибацией «Менеджер:/Клиент:» или JSON.
5. В поле "next_steps" — договорённость о следующем шаге, если она прозвучала.

Диалог:
---
{dialog_text}
---
"""


async def extract_profile_with_ai(dialog_text: str, ai: AIService) -> dict[str, str]:
    """Попросить модель заполнить анкету по сырому диалогу."""
    if not dialog_text.strip():
        raise ValueError("Пустой диалог — нечего извлекать")

    result = await ai.generate(
        system_prompt=build_extraction_prompt(dialog_text),
        messages=[{"role": "user", "content": dialog_text}],
    )
    _cleaned, profile = extract_profile(result.text)
    if profile is None:
        raise ValueError("Модель вернула ответ без JSON-анкеты")
    return profile


__all__ = (
    "PROJECT_ROOT",
    "build_extraction_prompt",
    "extract_profile_with_ai",
    "json_to_dialog_text",
    "load_source",
)
