"""Состояния диалога с пользователем (FSM vkbottle)."""

from __future__ import annotations

from vkbottle.dispatch.dispenser.base import BaseStateGroup


class RenameState(BaseStateGroup):
    """Ожидание нового названия диалога."""

    WAITING_TITLE = "waiting_title"
