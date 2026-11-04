"""Главная клавиатура бота."""

from __future__ import annotations

from vkbottle.tools.keyboard import Keyboard, KeyboardButtonColor, Text

NEW_DIALOG = "➕ Новый диалог"
DIALOGS = "📂 Мои диалоги"
SETTINGS = "⚙️ Настройки"
MODES = "🎭 Сменить режим"
HELP = "❓ Помощь"
RAG_STATUS = "📚 База знаний"

MENU_LABELS = (NEW_DIALOG, DIALOGS, SETTINGS, MODES, HELP)


def main_menu() -> Keyboard:
    """Постоянная клавиатура: 5 текстовых кнопок в двух рядах."""
    keyboard = Keyboard(one_time=False)
    keyboard.row()
    keyboard.add(Text(NEW_DIALOG), KeyboardButtonColor.POSITIVE)
    keyboard.add(Text(DIALOGS), KeyboardButtonColor.PRIMARY)
    keyboard.add(Text(SETTINGS), KeyboardButtonColor.SECONDARY)
    keyboard.row()
    keyboard.add(Text(MODES), KeyboardButtonColor.PRIMARY)
    keyboard.add(Text(HELP), KeyboardButtonColor.SECONDARY)
    return keyboard


def main_menu_with_rag() -> Keyboard:
    """Главная клавиатура с кнопкой базы знаний (RAG включён)."""
    keyboard = main_menu()
    keyboard.row()
    keyboard.add(Text(RAG_STATUS), KeyboardButtonColor.PRIMARY)
    return keyboard


__all__ = (
    "DIALOGS",
    "HELP",
    "MENU_LABELS",
    "MODES",
    "NEW_DIALOG",
    "RAG_STATUS",
    "SETTINGS",
    "main_menu",
    "main_menu_with_rag",
)


__all__ = (
    "DIALOGS",
    "HELP",
    "MENU_LABELS",
    "MODES",
    "NEW_DIALOG",
    "RAG_STATUS",
    "SETTINGS",
    "main_menu",
)
