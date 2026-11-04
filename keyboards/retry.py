"""Клавиатура повторной попытки после ошибки AI."""

from __future__ import annotations

from typing import Any

from vkbottle.tools.keyboard import KeyboardButtonColor

from .common import back_to_menu, callback_keyboard


def retry_keyboard() -> Any:
    rows: list[list[tuple[str, dict[str, Any], KeyboardButtonColor]]] = [
        [
            (
                "🔁 Повторить",
                {"cmd": "retry"},
                KeyboardButtonColor.POSITIVE,
            )
        ],
        [back_to_menu()],
    ]
    return callback_keyboard(rows)
