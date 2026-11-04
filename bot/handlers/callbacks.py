"""Обработка inline-кнопок (callback-события VK)."""

from __future__ import annotations

from typing import Any

from vkbottle.bot import BotLabeler, MessageEvent
from vkbottle_types.events import GroupEventType

from config import texts
from keyboards.dialogs import (
    clear_confirm_keyboard,
    delete_confirm_keyboard,
)
from utils.errors import DialogNotFoundError, LastDialogError

from ..flows import retry_last
from ..runtime import AppContext
from ..views import (
    edit_event,
    show_dialog_actions,
    show_dialogs,
    show_main,
    show_modes,
    show_settings,
)
from .dialogs import start_rename
from .helpers import profile_for
from .settings import apply_mode


def _page(payload: dict[str, Any]) -> int:
    try:
        return int(payload.get("page") or 0)
    except (TypeError, ValueError):
        return 0


def _dialog_id(payload: dict[str, Any]) -> str:
    return str(payload.get("id") or "")


def register(labeler: BotLabeler, ctx: AppContext) -> None:
    """Единая точка входа для всех inline-кнопок."""

    @labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent)
    async def on_callback(event: MessageEvent) -> None:
        payload = event.payload or {}
        command = str(payload.get("cmd") or "")

        if command == "menu":
            await ctx.bot.state_dispenser.delete(event.peer_id)
            profile = await profile_for(ctx, int(event.user_id))
            await show_main(ctx, event, profile)

        elif command == "dialogs":
            await show_dialogs(ctx, event)

        elif command == "dialogs_page":
            await show_dialogs(ctx, event, _page(payload))

        elif command == "dialog_open":
            await _open_dialog(ctx, event, _dialog_id(payload))

        elif command == "dialog_delete":
            await _ask_delete(ctx, event, _dialog_id(payload))

        elif command == "dialog_delete_confirm":
            await _delete_dialog(ctx, event, _dialog_id(payload))

        elif command == "dialog_clear":
            await _ask_clear(ctx, event, _dialog_id(payload))

        elif command == "dialog_clear_confirm":
            await _clear_dialog(ctx, event, _dialog_id(payload))

        elif command == "dialog_rename":
            await start_rename(ctx, event, _dialog_id(payload))

        elif command == "settings":
            await show_settings(ctx, event)

        elif command == "modes":
            await show_modes(ctx, event)

        elif command == "mode_set":
            await apply_mode(ctx, event, str(payload.get("mode") or ""))

        elif command == "retry":
            await retry_last(ctx, event)

        elif command == "noop":
            await event.show_snackbar(texts.CALLBACK_EXPIRED_TEXT)

        else:
            await event.show_snackbar(texts.CALLBACK_EXPIRED_TEXT)


async def _open_dialog(ctx: AppContext, event: MessageEvent, dialog_id: str) -> None:
    profile = await profile_for(ctx, int(event.user_id))
    try:
        dialog = ctx.dialogs.switch_dialog(profile, dialog_id)
    except DialogNotFoundError:
        await event.show_snackbar(texts.DIALOG_NOT_FOUND_TEXT)
        return
    await ctx.dialogs.save(profile)
    await show_dialog_actions(ctx, event, dialog)


async def _ask_delete(ctx: AppContext, event: MessageEvent, dialog_id: str) -> None:
    profile = await profile_for(ctx, int(event.user_id))
    dialog = profile.find_dialog(dialog_id)
    if dialog is None:
        await event.show_snackbar(texts.DIALOG_NOT_FOUND_TEXT)
        return
    if len(profile.dialogs) <= 1:
        await event.show_snackbar(texts.LAST_DIALOG_SHORT)
        return
    await edit_event(
        event,
        texts.delete_confirm_text(dialog),
        delete_confirm_keyboard(dialog.id),
    )


async def _delete_dialog(ctx: AppContext, event: MessageEvent, dialog_id: str) -> None:
    profile = await profile_for(ctx, int(event.user_id))
    try:
        ctx.dialogs.delete_dialog(profile, dialog_id)
    except LastDialogError:
        await event.show_snackbar(texts.LAST_DIALOG_SHORT)
        return
    except DialogNotFoundError:
        await event.show_snackbar(texts.DIALOG_NOT_FOUND_TEXT)
        return
    await ctx.dialogs.save(profile)
    await show_dialogs(ctx, event)


async def _ask_clear(ctx: AppContext, event: MessageEvent, dialog_id: str) -> None:
    profile = await profile_for(ctx, int(event.user_id))
    dialog = profile.find_dialog(dialog_id)
    if dialog is None:
        await event.show_snackbar(texts.DIALOG_NOT_FOUND_TEXT)
        return
    await edit_event(
        event,
        texts.clear_confirm_text(dialog),
        clear_confirm_keyboard(dialog.id),
    )


async def _clear_dialog(ctx: AppContext, event: MessageEvent, dialog_id: str) -> None:
    profile = await profile_for(ctx, int(event.user_id))
    try:
        ctx.dialogs.clear_dialog(profile, dialog_id)
    except DialogNotFoundError:
        await event.show_snackbar(texts.DIALOG_NOT_FOUND_TEXT)
        return
    await ctx.dialogs.save(profile)
    await show_settings(ctx, event)


__all__ = ("register",)
