"""Вспомогательные функции хендлеров."""

from __future__ import annotations

from models.user import UserProfile

from ..runtime import AppContext
from ..views import fetch_display_name


async def display_name(ctx: AppContext, user_id: int) -> str:
    """Имя пользователя с кэшем на время работы процесса."""
    cached = ctx.display_names.get(user_id)
    if cached is not None:
        return cached
    name = await fetch_display_name(ctx.api, user_id)
    ctx.display_names[user_id] = name
    return name


async def profile_for(ctx: AppContext, user_id: int) -> UserProfile:
    """Загрузить профиль, обновив отображаемое имя."""
    return await ctx.dialogs.get_profile(user_id, await display_name(ctx, user_id))


def is_cancel(text: str) -> bool:
    """Пользователь просит отменить текущее действие."""
    return text.strip().casefold() in {"/cancel", "отмена", "cancel"}
