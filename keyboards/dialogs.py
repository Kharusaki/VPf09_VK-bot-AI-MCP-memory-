"""Клавиатуры списка диалогов и подтверждений."""

from __future__ import annotations

from typing import Any

from vkbottle.tools.keyboard import KeyboardButtonColor

from models.dialog import Dialog
from models.user import UserProfile
from utils.text import truncate_utf16

from .common import callback_keyboard

DIALOGS_PER_PAGE = 4


def page_count(profile: UserProfile) -> int:
    """Количество страниц списка диалогов (минимум одна)."""
    return max(1, (len(profile.dialogs) + DIALOGS_PER_PAGE - 1) // DIALOGS_PER_PAGE)


def page_dialogs(profile: UserProfile, page: int) -> list[Dialog]:
    start = page * DIALOGS_PER_PAGE
    return profile.dialogs[start : start + DIALOGS_PER_PAGE]


def dialogs_keyboard(profile: UserProfile, page: int) -> Any:
    """4 диалога на страницу: кнопка выбора и кнопка удаления, плюс навигация."""
    pages = page_count(profile)
    page = min(max(0, page), pages - 1)

    rows: list[list[tuple[str, dict[str, Any], KeyboardButtonColor]]] = []
    for dialog in page_dialogs(profile, page):
        active = "✅ " if dialog.id == profile.active_dialog_id else "📄 "
        label = truncate_utf16(f"{active}{dialog.title}", 40)
        rows.append(
            [
                (
                    label,
                    {"cmd": "dialog_open", "id": dialog.id},
                    KeyboardButtonColor.PRIMARY
                    if dialog.id == profile.active_dialog_id
                    else KeyboardButtonColor.SECONDARY,
                ),
                (
                    "🗑",
                    {"cmd": "dialog_delete", "id": dialog.id},
                    KeyboardButtonColor.NEGATIVE,
                ),
            ]
        )

    rows.append(
        [
            (
                "◀️",
                {"cmd": "dialogs_page", "page": (page - 1) % pages},
                KeyboardButtonColor.SECONDARY,
            ),
            (
                "▶️",
                {"cmd": "dialogs_page", "page": (page + 1) % pages},
                KeyboardButtonColor.SECONDARY,
            ),
        ]
    )
    return callback_keyboard(rows)


def dialog_actions_keyboard(dialog_id: str) -> Any:
    """Действия с конкретным диалогом."""
    rows: list[list[tuple[str, dict[str, Any], KeyboardButtonColor]]] = [
        [
            (
                "✏️ Переименовать",
                {"cmd": "dialog_rename", "id": dialog_id},
                KeyboardButtonColor.SECONDARY,
            ),
            (
                "🧹 Очистить",
                {"cmd": "dialog_clear", "id": dialog_id},
                KeyboardButtonColor.SECONDARY,
            ),
        ],
        [
            (
                "🗑 Удалить",
                {"cmd": "dialog_delete", "id": dialog_id},
                KeyboardButtonColor.NEGATIVE,
            )
        ],
        [("📂 К списку", {"cmd": "dialogs"}, KeyboardButtonColor.SECONDARY)],
    ]
    return callback_keyboard(rows)


def delete_confirm_keyboard(dialog_id: str) -> Any:
    rows: list[list[tuple[str, dict[str, Any], KeyboardButtonColor]]] = [
        [
            (
                "✅ Удалить",
                {"cmd": "dialog_delete_confirm", "id": dialog_id},
                KeyboardButtonColor.NEGATIVE,
            )
        ],
        [
            (
                "⬅️ Отмена",
                {"cmd": "dialogs"},
                KeyboardButtonColor.SECONDARY,
            )
        ],
    ]
    return callback_keyboard(rows)


def clear_confirm_keyboard(dialog_id: str) -> Any:
    rows: list[list[tuple[str, dict[str, Any], KeyboardButtonColor]]] = [
        [
            (
                "✅ Очистить",
                {"cmd": "dialog_clear_confirm", "id": dialog_id},
                KeyboardButtonColor.POSITIVE,
            )
        ],
        [
            (
                "⬅️ Отмена",
                {"cmd": "settings"},
                KeyboardButtonColor.SECONDARY,
            )
        ],
    ]
    return callback_keyboard(rows)


__all__ = (
    "DIALOGS_PER_PAGE",
    "clear_confirm_keyboard",
    "delete_confirm_keyboard",
    "dialog_actions_keyboard",
    "dialogs_keyboard",
    "page_count",
    "page_dialogs",
)
