"""Команды и кнопки главного меню."""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch.rules.base import CommandRule, RegexRule, StateRule

from config import texts
from keyboards.main import (
    DIALOGS,
    HELP,
    MODES,
    NEW_DIALOG,
    RAG_STATUS,
    SETTINGS,
    main_menu,
)
from utils.errors import DialogLimitError

from ..rules import text_in
from ..runtime import AppContext
from ..views import (
    show_dialogs,
    show_help,
    show_main,
    show_modes,
    show_rag_status,
    show_settings,
)
from .helpers import profile_for


def register(labeler: BotLabeler, ctx: AppContext) -> None:
    """Зарегистрировать команды и текстовые кнопки меню."""

    @labeler.private_message(StateRule(None), CommandRule("start"))
    async def start(message: Message) -> None:
        profile = await profile_for(ctx, int(message.from_id))
        await show_main(ctx, message, profile)

    @labeler.private_message(StateRule(None), CommandRule("help"))
    async def help_command(message: Message) -> None:
        await show_help(ctx, message)

    @labeler.private_message(StateRule(None), CommandRule("cancel"))
    async def cancel_command(message: Message) -> None:
        await ctx.bot.state_dispenser.delete(message.peer_id)
        await ctx.messaging.send(message.peer_id, texts.CANCEL_TEXT, main_menu())

    @labeler.private_message(StateRule(None), text_in(NEW_DIALOG))
    async def new_dialog(message: Message) -> None:
        profile = await profile_for(ctx, int(message.from_id))
        try:
            dialog = ctx.dialogs.new_dialog(profile)
        except DialogLimitError:
            await ctx.messaging.send(
                message.peer_id,
                texts.DIALOG_LIMIT_TEXT.format(limit=ctx.settings.max_dialogs),
                main_menu(),
            )
            return
        await ctx.dialogs.save(profile)
        await ctx.messaging.send(
            message.peer_id,
            texts.dialog_created_text(dialog),
            main_menu(),
        )

    @labeler.private_message(StateRule(None), text_in(DIALOGS))
    async def dialogs(message: Message) -> None:
        await show_dialogs(ctx, message)

    @labeler.private_message(StateRule(None), text_in(SETTINGS))
    async def settings(message: Message) -> None:
        await show_settings(ctx, message)

    @labeler.private_message(StateRule(None), text_in(MODES))
    async def modes(message: Message) -> None:
        await show_modes(ctx, message)

    @labeler.private_message(StateRule(None), text_in(HELP))
    async def help_button(message: Message) -> None:
        await show_help(ctx, message)

    @labeler.private_message(StateRule(None), text_in(RAG_STATUS))
    async def rag_status(message: Message) -> None:
        await show_rag_status(ctx, message)

    @labeler.private_message(StateRule(None), RegexRule(r"^/\S+"))
    async def unknown_command(message: Message) -> None:
        await ctx.messaging.send(
            message.peer_id, texts.UNKNOWN_COMMAND_TEXT, main_menu()
        )


__all__ = ("register",)
