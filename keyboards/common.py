"""Общие inline-кнопки и ограничения клавиатур.

VK ограничивает inline-клавиатуру 10 кнопками и 6 рядами, подпись кнопки —
40 символами, payload — 255 символами. Проверки собраны здесь, чтобы ни один
экран не отправил заведомо невалидную клавиатуру.
"""

from __future__ import annotations

import json
from typing import Any

from vkbottle.tools.keyboard import Callback, Keyboard, KeyboardButtonColor

from utils.text import truncate_utf16

MAX_LABEL = 40
MAX_PAYLOAD = 255
MAX_ROWS = 6
MAX_BUTTONS = 10

Payload = dict[str, Any] | str


def payload_size(payload: Payload) -> int:
    """Размер payload в байтах UTF-8 так, как его увидит VK."""
    if isinstance(payload, str):
        raw = payload
    else:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return len(raw.encode("utf-8"))


def validate_rows(rows: list[list[tuple[str, Payload, KeyboardButtonColor]]]) -> None:
    """Проверить ограничения inline-клавиатуры до сборки."""
    if len(rows) > MAX_ROWS:
        raise ValueError(f"рядов в клавиатуре больше {MAX_ROWS}: {len(rows)}")

    total = sum(len(row) for row in rows)
    if total > MAX_BUTTONS:
        raise ValueError(f"кнопок в клавиатуре больше {MAX_BUTTONS}: {total}")

    for row in rows:
        if not row:
            raise ValueError("пустой ряд клавиатуры")
        for label, payload, _color in row:
            if not label.strip():
                raise ValueError("пустая подпись кнопки")
            if payload_size(payload) > MAX_PAYLOAD:
                raise ValueError(
                    f"payload кнопки «{label}» больше {MAX_PAYLOAD} байт"
                )


def callback_keyboard(
    rows: list[list[tuple[str, Payload, KeyboardButtonColor]]],
) -> Keyboard:
    """Собрать inline-клавиатуру из строк (label, payload, color)."""
    validate_rows(rows)

    keyboard = Keyboard(inline=True)
    for row in rows:
        keyboard.row()
        for label, payload, color in row:
            keyboard.add(Callback(truncate_utf16(label, MAX_LABEL), payload), color)
    return keyboard


def back_to_menu() -> tuple[str, Payload, KeyboardButtonColor]:
    return ("⬅️ В меню", {"cmd": "menu"}, KeyboardButtonColor.SECONDARY)


def cancel() -> tuple[str, Payload, KeyboardButtonColor]:
    return ("⬅️ Отмена", {"cmd": "menu"}, KeyboardButtonColor.SECONDARY)


def rename_keyboard() -> Keyboard:
    """Клавиатура ожидания нового названия диалога."""
    return callback_keyboard([[cancel()]])


__all__ = (
    "MAX_BUTTONS",
    "MAX_LABEL",
    "MAX_PAYLOAD",
    "MAX_ROWS",
    "Payload",
    "back_to_menu",
    "callback_keyboard",
    "cancel",
    "payload_size",
    "rename_keyboard",
    "validate_rows",
)
