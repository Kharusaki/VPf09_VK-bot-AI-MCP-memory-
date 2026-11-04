"""Клавиатура выбора режима общения."""

from __future__ import annotations

from typing import Any

from vkbottle.tools.keyboard import KeyboardButtonColor

from models.enums import Mode

from .common import back_to_menu, callback_keyboard

MODES_PER_ROW = 2


def modes_keyboard(current: Mode) -> Any:
    """Пять режимов и возврат в меню."""
    modes = list(Mode)
    rows: list[list[tuple[str, dict[str, Any], KeyboardButtonColor]]] = []

    for index in range(0, len(modes), MODES_PER_ROW):
        row: list[tuple[str, dict[str, Any], KeyboardButtonColor]] = []
        for mode in modes[index : index + MODES_PER_ROW]:
            active = mode is current
            label = f"✅ {mode.label}" if active else mode.label
            row.append(
                (
                    label,
                    {"cmd": "mode_set", "mode": mode.value},
                    KeyboardButtonColor.POSITIVE
                    if active
                    else KeyboardButtonColor.SECONDARY,
                )
            )
        rows.append(row)

    rows.append([back_to_menu()])
    return callback_keyboard(rows)
