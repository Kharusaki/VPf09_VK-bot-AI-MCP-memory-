"""Хендлеры VK-бота."""

from __future__ import annotations

from vkbottle.bot import BotLabeler

from ..runtime import AppContext
from . import callbacks, common, dialogs, messages


def register_handlers(labeler: BotLabeler, ctx: AppContext) -> None:
    """Подключить все обработчики в правильном порядке.

    Сценарий переименования регистрируется первым: пока пользователь вводит
    название, его текст не должен попадать в меню или AI-диалог.
    """
    dialogs.register(labeler, ctx)
    common.register(labeler, ctx)
    messages.register(labeler, ctx)
    callbacks.register(labeler, ctx)


__all__ = ("register_handlers",)
