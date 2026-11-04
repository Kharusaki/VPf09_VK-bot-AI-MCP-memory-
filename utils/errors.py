"""Доменные исключения приложения.

Все ошибки, которые должны быть понятны обработчикам, наследуются от AppError.
Это позволяет не ловить случайные исключения там, где нужна конкретная реакция.
"""

from __future__ import annotations


class AppError(Exception):
    """Базовая ошибка приложения."""


class ConfigError(AppError):
    """Некорректная или неполная конфигурация."""


class StorageError(AppError):
    """MCP-хранилище недоступно или вернуло ошибку."""


class AIError(AppError):
    """Ошибка AI-провайдера."""


class AIUnavailableError(AIError):
    """Не удалось получить ответ ни от основной, ни от резервной модели."""


class DialogError(AppError):
    """Ошибка операции с диалогом."""


class DialogNotFoundError(DialogError):
    """Диалог не найден в профиле пользователя."""


class DialogLimitError(DialogError):
    """Достигнут лимит количества диалогов."""


class LastDialogError(DialogError):
    """Нельзя удалить единственный диалог."""
