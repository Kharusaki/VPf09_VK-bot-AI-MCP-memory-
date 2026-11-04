"""Клавиатуры бота."""

from .common import callback_keyboard, rename_keyboard
from .dialogs import (
    DIALOGS_PER_PAGE,
    clear_confirm_keyboard,
    delete_confirm_keyboard,
    dialog_actions_keyboard,
    dialogs_keyboard,
    page_count,
    page_dialogs,
)
from .main import (
    DIALOGS,
    HELP,
    MENU_LABELS,
    MODES,
    NEW_DIALOG,
    SETTINGS,
    main_menu,
)
from .modes import modes_keyboard
from .retry import retry_keyboard
from .settings import settings_keyboard

__all__ = (
    "DIALOGS",
    "DIALOGS_PER_PAGE",
    "HELP",
    "MENU_LABELS",
    "MODES",
    "NEW_DIALOG",
    "SETTINGS",
    "callback_keyboard",
    "clear_confirm_keyboard",
    "delete_confirm_keyboard",
    "dialog_actions_keyboard",
    "dialogs_keyboard",
    "main_menu",
    "modes_keyboard",
    "page_count",
    "page_dialogs",
    "rename_keyboard",
    "retry_keyboard",
    "settings_keyboard",
)
