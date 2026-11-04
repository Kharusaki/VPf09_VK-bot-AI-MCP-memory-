"""Клавиатура экрана настроек."""

from __future__ import annotations

from typing import Any

from vkbottle.tools.keyboard import KeyboardButtonColor

from .common import back_to_menu, callback_keyboard


def settings_keyboard(dialog_id: str) -> Any:
    """Действия с активным диалогом."""
    rows: list[list[tuple[str, dict[str, Any], KeyboardButtonColor]]] = [
        [
            (
                "🎭 Сменить режим",
                {"cmd": "modes"},
                KeyboardButtonColor.PRIMARY,
            ),
            (
                "✏️ Переименовать",
                {"cmd": "dialog_rename", "id": dialog_id},
                KeyboardButtonColor.SECONDARY,
            ),
        ],
        [
            (
                "🧹 Очистить историю",
                {"cmd": "dialog_clear", "id": dialog_id},
                KeyboardButtonColor.NEGATIVE,
            )
        ],
        [back_to_menu()],
    ]
    return callback_keyboard(rows)
