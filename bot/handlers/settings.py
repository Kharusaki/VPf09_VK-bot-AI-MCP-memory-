"""Смена режима общения активного диалога."""

from __future__ import annotations

from vkbottle.bot import MessageEvent

from config import texts
from models.enums import Mode
from utils.errors import DialogNotFoundError

from ..runtime import AppContext
from ..views import show_modes
from .helpers import profile_for


async def apply_mode(ctx: AppContext, event: MessageEvent, value: str) -> None:
    """Применить выбранный режим и показать обновлённый экран."""
    profile = await profile_for(ctx, int(event.user_id))
    try:
        ctx.dialogs.set_mode(profile, Mode.from_value(value))
    except DialogNotFoundError:
        await event.show_snackbar(texts.DIALOG_NOT_FOUND_TEXT)
        return

    await ctx.dialogs.save(profile)
    await show_modes(ctx, event)


__all__ = ("apply_mode",)
