"""Главная клавиатура бота."""

from __future__ import annotations

from vkbottle.tools.keyboard import Keyboard, KeyboardButtonColor, Text

NEW_DIALOG = "➕ Новый диалог"
DIALOGS = "📂 Мои диалоги"
SETTINGS = "⚙️ Настройки"
MODES = "🎭 Сменить режим"
HELP = "❓ Помощь"

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
