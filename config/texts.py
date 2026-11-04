"""Все тексты интерфейса на русском языке.

Тексты вынесены из хендлеров, чтобы менять формулировки без правки логики.
"""

from __future__ import annotations

from models.dialog import Dialog
from models.enums import Mode
from models.user import UserProfile

THINKING = "🤔 Думаю…"

EMPTY_TEXT = "Сообщение пустое. Напишите вопрос или выберите действие на клавиатуре."

UNSUPPORTED_TEXT = (
    "Я понимаю только текст. 📝\n"
    "Опишите вопрос сообщением — и я помогу."
)

TOO_LONG_TEXT = (
    "Сообщение слишком длинное ({length} символов при лимите {limit}).\n"
    "Сократите его и отправьте ещё раз."
)

AI_ERROR_TEXT = (
    "😔 Не удалось получить ответ: AI-сервис временно недоступен.\n\n"
    "Попробуйте повторить запрос через минуту."
)

STORAGE_ERROR_TEXT = (
    "😔 Хранилище диалогов временно недоступно.\n"
    "Попробуйте ещё раз через несколько секунд."
)

NETWORK_ERROR_TEXT = (
    "😔 Похоже, пропала связь с сервисом.\n"
    "Проверьте интернет и попробуйте снова."
)

RETRY_NOT_FOUND_TEXT = "Не нашёл сообщение для повтора. Отправьте его ещё раз."

UNKNOWN_COMMAND_TEXT = (
    "Неизвестная команда. Нажмите /start, чтобы открыть главное меню."
)

CALLBACK_EXPIRED_TEXT = "Кнопка устарела. Откройте меню заново."

DIALOG_NOT_FOUND_TEXT = "Диалог не найден. Возможно, он уже удалён."

CANCEL_TEXT = "Действие отменено. Вы в главном меню 👇"

TITLE_PROMPT_TEXT = (
    "✏️ Отправьте новое название диалога одним сообщением.\n"
    "До 50 символов. /cancel — отмена."
)

TITLE_INVALID_TEXT = "Название должно быть от 1 до 50 символов. Попробуйте ещё раз."

LAST_DIALOG_TEXT = (
    "Нельзя удалить единственный диалог.\n"
    "Создайте новый диалог или очистите историю текущего."
)

LAST_DIALOG_SHORT = "Нельзя удалить единственный диалог."

DIALOG_LIMIT_TEXT = (
    "Достигнут лимит диалогов ({limit}).\n"
    "Удалите один из старых диалогов, чтобы создать новый."
)

MENU_HINT = "Главное меню 👇"


def start_text(profile: UserProfile) -> str:
    """Приветствие с информацией об активном диалоге."""
    dialog = profile.active_dialog
    if dialog is None:
        return (
            "Привет! 👋\n\n"
            "Я AI-помощник во ВКонтакте. Умею вести несколько независимых диалогов, "
            "запоминать контекст и менять стиль общения.\n\n"
            "Напишите сообщение или выберите действие на клавиатуре."
        )
    return (
        "Привет! 👋\n\n"
        "Я AI-помощник во ВКонтакте. Умею вести несколько независимых диалогов, "
        "запоминать контекст и менять стиль общения.\n\n"
        f"Активный диалог: «{dialog.title}»\n"
        f"Режим: {dialog.mode.label}\n\n"
        "Напишите сообщение или выберите действие на клавиатуре."
    )


def help_text() -> str:
    """Справка по возможностям бота."""
    return (
        "❓ Помощь\n\n"
        "Что я умею:\n"
        "• вести несколько диалогов с отдельной историей;\n"
        "• запоминать последние 100 сообщений;\n"
        "• менять стиль общения в пяти режимах;\n"
        "• переименовывать диалоги и очищать историю.\n\n"
        "Кнопки:\n"
        "➕ Новый диалог — создать ещё один диалог.\n"
        "📂 Мои диалоги — переключиться или удалить.\n"
        "⚙️ Настройки — режим, модель, очистка истории.\n"
        "🎭 Сменить режим — быстрый выбор роли.\n\n"
        "Просто отправьте текст — я отвечу с учётом контекста."
    )


def dialogs_text(profile: UserProfile, page: int, pages: int, max_dialogs: int) -> str:
    """Заголовок экрана со списком диалогов."""
    active = profile.active_dialog
    active_title = active.title if active else "—"
    return (
        f"📂 Ваши диалоги — страница {page + 1} из {pages}\n\n"
        f"Активный: «{active_title}»\n"
        f"Всего диалогов: {len(profile.dialogs)} из {max_dialogs}\n\n"
        "Нажмите на название, чтобы переключиться, или 🗑, чтобы удалить."
    )


def settings_text(profile: UserProfile, dialog: Dialog | None, model: str) -> str:
    """Экран настроек активного диалога."""
    if dialog is None:
        return "⚙️ Настройки\n\nАктивный диалог не найден. Создайте новый диалог."

    return (
        "⚙️ Настройки\n\n"
        f"Активный диалог: «{dialog.title}»\n"
        f"Режим: {dialog.mode.label}\n"
        f"Модель: {model}\n"
        f"Сообщений в истории: {dialog.message_count} из 100\n\n"
        "Выберите действие."
    )


def modes_text(current: Mode) -> str:
    """Экран выбора режима общения."""
    return (
        "🎭 Выберите режим общения\n\n"
        f"Сейчас активен: {current.label}\n\n"
        "Режим применяется только к текущему диалогу. "
        "История при смене режима сохраняется."
    )


def delete_confirm_text(dialog: Dialog) -> str:
    """Подтверждение удаления диалога."""
    return (
        f"Удалить диалог «{dialog.title}»?\n\n"
        f"Его история ({dialog.message_count} сообщений) будет потеряна безвозвратно."
    )


def clear_confirm_text(dialog: Dialog) -> str:
    """Подтверждение очистки истории."""
    return (
        f"Очистить историю диалога «{dialog.title}»?\n\n"
        f"Будут удалены все {dialog.message_count} сообщений. "
        "Сам диалог и выбранный режим останутся."
    )


def dialog_created_text(dialog: Dialog) -> str:
    return (
        f"✅ Создан новый диалог «{dialog.title}».\n"
        f"Режим: {dialog.mode.label}\n\n"
        "Можно писать сообщение."
    )


def dialog_switched_text(dialog: Dialog) -> str:
    return (
        f"🔀 Переключились на диалог «{dialog.title}».\n"
        f"Режим: {dialog.mode.label}\n"
        f"Сообщений в истории: {dialog.message_count}"
    )


def dialog_deleted_text(title: str) -> str:
    return f"🗑 Диалог «{title}» удалён."


def dialog_renamed_text(title: str) -> str:
    return f"✏️ Диалог переименован в «{title}»."


def mode_changed_text(mode: Mode) -> str:
    return f"🎭 Режим изменён: {mode.label}"


def history_cleared_text(title: str) -> str:
    return f"🧹 История диалога «{title}» очищена."


def model_line(model: str) -> str:
    return f"Модель: {model}"
