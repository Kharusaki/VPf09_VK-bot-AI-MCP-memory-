"""Работа с текстом: UTF-16, очистка и разбивка под лимит VK.

VK ограничивает сообщение 4096 символами, но считает их в UTF-16. Эмодзи
занимают две единицы, поэтому обычный len() может занизить длину и привести
к ошибке 100 от API. Все проверки длины выполняются через utf16_len().
"""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"[ \t]+")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SENTENCE_ENDINGS = frozenset(".!?…")


def utf16_len(text: str) -> int:
    """Длина строки в единицах UTF-16 (как считает VK)."""
    return len(text.encode("utf-16-le")) // 2


def clean_text(text: str | None) -> str:
    """Нормализовать пользовательский текст, не ломая абзацы."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_utf16(text: str, limit: int) -> str:
    """Обрезать строку до limit единиц UTF-16, не разрезая эмодзи."""
    if limit <= 0:
        return ""
    units = 0
    end = 0
    for index, char in enumerate(text):
        char_units = 2 if ord(char) > 0xFFFF else 1
        if units + char_units > limit:
            break
        units += char_units
        end = index + 1
    return text[:end]


def normalize_title(raw: str | None, limit: int = 50) -> str:
    """Привести название диалога к одному пробелу и обрезать по лимиту."""
    text = " ".join((raw or "").split())
    return truncate_utf16(text, limit).strip()


def _prefix_end(text: str, limit: int) -> int:
    """Индекс, до которого строка помещается в limit единиц UTF-16."""
    units = 0
    for index, char in enumerate(text):
        char_units = 2 if ord(char) > 0xFFFF else 1
        if units + char_units > limit:
            return index
        units += char_units
    return len(text)


def _find_cut(text: str, limit: int) -> int:
    """Найти красивое место разреза: абзац, предложение или пробел."""
    end = _prefix_end(text, limit)
    if end <= 0:
        return 0

    window_start = max(0, int(end * 0.55))

    for index in range(end - 1, window_start - 1, -1):
        char = text[index]
        if char == "\n":
            return index + 1
        if char in _SENTENCE_ENDINGS and index + 1 < len(text) and text[index + 1] in " \n":
            return index + 1

    space = text.rfind(" ", window_start, end)
    if space > 0:
        return space + 1
    return end


def split_text(text: str, limit: int = 3800) -> list[str]:
    """Разбить длинный ответ на части, не превышающие лимит VK."""
    text = text.strip()
    if not text:
        return []

    limit = max(100, int(limit))
    if utf16_len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if utf16_len(remaining) <= limit:
            chunks.append(remaining)
            break

        cut = _find_cut(remaining, limit)
        if cut <= 0:
            cut = _prefix_end(remaining, limit)

        chunk = remaining[:cut].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut:].lstrip()

    return chunks
