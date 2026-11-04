"""Сценарий переименования диалога."""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message, MessageEvent
from vkbottle.dispatch.rules.base import StateRule

from config import texts
from keyboards.common import rename_keyboard
from keyboards.main import main_menu
from utils.errors import DialogNotFoundError
from utils.text import clean_text

from ..runtime import AppContext
from ..states import RenameState
from ..views import edit_event
from .helpers import is_cancel, profile_for


def register(labeler: BotLabeler, ctx: AppContext) -> None:
    """Ожидание нового названия диалога."""

    @labeler.private_message(StateRule(RenameState.WAITING_TITLE))
    async def rename_title(message: Message) -> None:
        state = await ctx.bot.state_dispenser.get(message.peer_id)
        dialog_id = str((state.payload or {}).get("dialog_id") or "") if state else ""

        if is_cancel(message.text or ""):
            await ctx.bot.state_dispenser.delete(message.peer_id)
            await ctx.messaging.send(message.peer_id, texts.CANCEL_TEXT, main_menu())
            return

        profile = await profile_for(ctx, int(message.from_id))
        try:
            dialog = ctx.dialogs.rename_dialog(profile, dialog_id, clean_text(message.text))
        except DialogNotFoundError:
            await ctx.bot.state_dispenser.delete(message.peer_id)
            await ctx.messaging.send(
                message.peer_id, texts.DIALOG_NOT_FOUND_TEXT, main_menu()
            )
            return
        except ValueError:
            await ctx.messaging.send(
                message.peer_id, texts.TITLE_INVALID_TEXT, rename_keyboard()
            )
            return

        await ctx.dialogs.save(profile)
        await ctx.bot.state_dispenser.delete(message.peer_id)
        await ctx.messaging.send(
            message.peer_id,
            texts.dialog_renamed_text(dialog.title),
            main_menu(),
        )


async def start_rename(ctx: AppContext, event: MessageEvent, dialog_id: str) -> None:
    """Перевести пользователя в состояние ввода нового названия."""
    profile = await profile_for(ctx, int(event.user_id))
    dialog = profile.find_dialog(dialog_id)
    if dialog is None:
        await event.show_snackbar(texts.DIALOG_NOT_FOUND_TEXT)
        return

    await ctx.bot.state_dispenser.set(
        event.peer_id, RenameState.WAITING_TITLE, dialog_id=dialog.id
    )
    await edit_event(event, texts.TITLE_PROMPT_TEXT, rename_keyboard())


__all__ = ("register", "start_rename")
