"""Обработка обычных текстовых сообщений."""

from __future__ import annotations

from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch.rules.base import StateRule

from config import texts
from keyboards.main import main_menu

from ..flows import process_text
from ..runtime import AppContext
from .helpers import display_name


def register(labeler: BotLabeler, ctx: AppContext) -> None:
    """Все сообщения вне состояний уходят в AI-диалог."""

    @labeler.private_message(StateRule(None))
    async def on_message(message: Message) -> None:
        text = message.text or ""
        if not text.strip():
            reply = texts.UNSUPPORTED_TEXT if message.attachments else texts.EMPTY_TEXT
            await ctx.messaging.send(message.peer_id, reply, main_menu())
            return

        await process_text(
            ctx,
            int(message.peer_id),
            int(message.from_id),
            text,
            await display_name(ctx, int(message.from_id)),
        )


__all__ = ("register",)
