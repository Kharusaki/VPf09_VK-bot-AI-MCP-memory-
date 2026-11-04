"""Тесты клавиатур: лимиты VK и содержимое экранов."""

from __future__ import annotations

import json

import pytest
from vkbottle.tools.keyboard import KeyboardButtonColor

from keyboards.common import (
    MAX_BUTTONS,
    MAX_LABEL,
    MAX_ROWS,
    callback_keyboard,
    payload_size,
    rename_keyboard,
    validate_rows,
)
from keyboards.dialogs import (
    clear_confirm_keyboard,
    delete_confirm_keyboard,
    dialog_actions_keyboard,
    dialogs_keyboard,
    page_count,
    page_dialogs,
)
from keyboards.main import main_menu
from keyboards.modes import modes_keyboard
from keyboards.retry import retry_keyboard
from keyboards.settings import settings_keyboard
from models.dialog import Dialog
from models.enums import Mode
from models.user import UserProfile
from utils.text import utf16_len
from utils.time import utc_now


def _profile(count: int) -> UserProfile:
    now = utc_now()
    dialogs = [
        Dialog(
            id=f"dialog-{index:02d}",
            title=f"Диалог {index + 1}",
            mode=Mode.ASSISTANT,
            created_at=now,
            updated_at=now,
        )
        for index in range(count)
    ]
    return UserProfile(
        user_id=1,
        display_name="Тест",
        created_at=now,
        updated_at=now,
        active_dialog_id=dialogs[0].id if dialogs else "",
        dialog_counter=count + 1,
        dialogs=dialogs,
    )


def _buttons(keyboard) -> list[dict]:
    data = json.loads(keyboard.get_json())
    return [button for row in data["buttons"] for button in row]


def _assert_inline_limits(keyboard) -> None:
    data = json.loads(keyboard.get_json())
    rows = data["buttons"]
    buttons = [button for row in rows for button in row]

    assert data["inline"] is True
    assert len(rows) <= MAX_ROWS
    assert len(buttons) <= MAX_BUTTONS
    for button in buttons:
        action = button["action"]
        assert action["type"] == "callback"
        assert action["label"].strip()
        assert utf16_len(action["label"]) <= MAX_LABEL
        assert payload_size(action["payload"]) <= 255


def test_main_menu_is_text_keyboard_with_five_buttons() -> None:
    data = json.loads(main_menu().get_json())

    assert data["inline"] is False
    assert len(data["buttons"]) == 2
    assert sum(len(row) for row in data["buttons"]) == 5
    assert all(button["action"]["type"] == "text" for button in _buttons(main_menu()))


def test_all_inline_keyboards_fit_vk_limits() -> None:
    profile = _profile(20)
    keyboards = [
        dialogs_keyboard(profile, 0),
        dialogs_keyboard(profile, 4),
        dialog_actions_keyboard("dialog-00"),
        delete_confirm_keyboard("dialog-00"),
        clear_confirm_keyboard("dialog-00"),
        settings_keyboard("dialog-00"),
        modes_keyboard(Mode.ASSISTANT),
        retry_keyboard(),
        rename_keyboard(),
    ]

    for keyboard in keyboards:
        _assert_inline_limits(keyboard)


def test_dialogs_pagination() -> None:
    profile = _profile(10)

    assert page_count(profile) == 3
    assert len(page_dialogs(profile, 0)) == 4
    assert len(page_dialogs(profile, 2)) == 2
    assert page_dialogs(profile, 2)[0].id == "dialog-08"


def test_dialogs_keyboard_has_four_dialogs_and_navigation() -> None:
    keyboard = dialogs_keyboard(_profile(10), 0)
    buttons = _buttons(keyboard)

    assert len(buttons) == 10
    commands = [button["action"]["payload"]["cmd"] for button in buttons]
    assert commands.count("dialog_open") == 4
    assert commands.count("dialog_delete") == 4
    assert commands.count("dialogs_page") == 2


def test_long_dialog_title_is_truncated_in_button() -> None:
    profile = _profile(1)
    profile.dialogs[0].title = "Очень длинное название диалога, которое не помещается"

    keyboard = dialogs_keyboard(profile, 0)
    labels = [button["action"]["label"] for button in _buttons(keyboard)]

    assert all(utf16_len(label) <= MAX_LABEL for label in labels)


def test_modes_keyboard_marks_current_mode() -> None:
    buttons = _buttons(modes_keyboard(Mode.PROGRAMMER))
    labels = [button["action"]["label"] for button in buttons]

    assert any(label.startswith("✅") and "Программист" in label for label in labels)
    assert sum(1 for label in labels if label.startswith("✅")) == 1


def test_payload_size_for_dict_and_string() -> None:
    assert payload_size({"cmd": "menu"}) == len('{"cmd":"menu"}')
    assert payload_size("abc") == 3


def test_callback_keyboard_rejects_too_many_buttons() -> None:
    row = [("Кнопка", {"cmd": "x"}, KeyboardButtonColor.SECONDARY)] * 6
    with pytest.raises(ValueError, match="кнопок"):
        callback_keyboard([row, row])


def test_callback_keyboard_rejects_too_many_rows() -> None:
    row = [("Кнопка", {"cmd": "x"}, KeyboardButtonColor.SECONDARY)]
    with pytest.raises(ValueError, match="рядов"):
        callback_keyboard([row] * (MAX_ROWS + 1))


def test_callback_keyboard_rejects_large_payload() -> None:
    rows = [[("Кнопка", {"cmd": "x", "id": "a" * 300}, KeyboardButtonColor.SECONDARY)]]
    with pytest.raises(ValueError, match="payload"):
        validate_rows(rows)
    with pytest.raises(ValueError, match="payload"):
        callback_keyboard(rows)


def test_callback_keyboard_rejects_empty_row_and_label() -> None:
    with pytest.raises(ValueError, match="пустой ряд"):
        callback_keyboard([[]])
    with pytest.raises(ValueError, match="подпись"):
        callback_keyboard([[("   ", {"cmd": "x"}, KeyboardButtonColor.SECONDARY)]])
