"""Отрисовка экранов бота.

Один и тот же экран показывается либо новым сообщением (после текстовой
команды), либо редактированием сообщения с inline-кнопкой. Редактирование
убирает старую клавиатуру, чтобы по ней нельзя было нажать дважды.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any

from vkbottle.bot import Message, MessageEvent
from vkbottle.tools.keyboard import Keyboard

from config.texts import (
    dialogs_text,
    help_text,
    modes_text,
    settings_text,
    start_text,
)
from keyboards.dialogs import dialogs_keyboard, page_count
from keyboards.main import main_menu, main_menu_with_rag
from keyboards.modes import modes_keyboard
from keyboards.settings import settings_keyboard
from models.dialog import Dialog
from models.user import UserProfile

from .runtime import AppContext

logger = logging.getLogger(__name__)

EMPTY_INLINE = Keyboard(inline=True).get_json()


def target_user_id(target: Message | MessageEvent) -> int:
    """ID пользователя для сообщения или callback-события."""
    if isinstance(target, MessageEvent):
        return int(target.user_id)
    return int(target.from_id)


def target_peer_id(target: Message | MessageEvent) -> int:
    return int(target.peer_id)


async def edit_event(
    event: MessageEvent,
    text: str,
    keyboard: Keyboard | None = None,
) -> None:
    """Отредактировать сообщение с кнопкой и закрыть callback."""
    keyboard_json = keyboard.get_json() if keyboard is not None else EMPTY_INLINE
    try:
        await event.ctx_api.messages.edit(
            peer_id=event.peer_id,
            cmid=event.conversation_message_id,
            message=text,
            keyboard=keyboard_json,
        )
    except Exception as exc:
        logger.warning("Не удалось отредактировать callback-сообщение: %s", exc)
        with suppress(Exception):
            await event.ctx_api.messages.send(
                peer_id=event.peer_id,
                message=text,
                keyboard=keyboard_json,
            )
    finally:
        with suppress(Exception):
            await event.send_empty_answer()


async def answer_screen(
    ctx: AppContext,
    target: Message | MessageEvent,
    text: str,
    keyboard: Keyboard | None = None,
) -> None:
    """Показать экран новым сообщением или правкой текущего."""
    if isinstance(target, MessageEvent):
        await edit_event(target, text, keyboard)
        return
    await ctx.messaging.send(target_peer_id(target), text, keyboard)


async def fetch_display_name(api: Any, user_id: int) -> str:
    """Имя пользователя для профиля. Ошибка не критична."""
    try:
        users = await api.users.get(user_ids=[user_id], fields=["first_name", "last_name"])
    except Exception as exc:
        logger.debug("Не удалось получить имя пользователя %s: %s", user_id, exc)
        return ""
    if not users:
        return ""
    user = users[0]
    name = " ".join(
        part for part in (getattr(user, "first_name", ""), getattr(user, "last_name", "")) if part
    )
    return name.strip()


async def show_main(
    ctx: AppContext,
    target: Message | MessageEvent,
    profile: UserProfile,
) -> None:
    keyboard = main_menu_with_rag() if (ctx.settings.rag_enabled and ctx.rag and ctx.rag.chunk_count) else main_menu()
    await answer_screen(ctx, target, start_text(profile), keyboard)


async def show_help(ctx: AppContext, target: Message | MessageEvent) -> None:
    await answer_screen(ctx, target, help_text(), main_menu())


async def show_dialogs(
    ctx: AppContext,
    target: Message | MessageEvent,
    page: int = 0,
) -> None:
    user_id = target_user_id(target)
    profile = await ctx.dialogs.get_profile(user_id)
    pages = page_count(profile)
    page = min(max(0, page), pages - 1)
    await answer_screen(
        ctx,
        target,
        dialogs_text(profile, page, pages, ctx.settings.max_dialogs),
        dialogs_keyboard(profile, page),
    )


async def show_settings(ctx: AppContext, target: Message | MessageEvent) -> None:
    user_id = target_user_id(target)
    profile = await ctx.dialogs.get_profile(user_id)
    dialog = profile.active_dialog
    if dialog is None:
        await answer_screen(ctx, target, "Активный диалог не найден.", main_menu())
        return
    await answer_screen(
        ctx,
        target,
        settings_text(profile, dialog, ctx.settings.primary_model),
        settings_keyboard(dialog.id),
    )


async def show_modes(ctx: AppContext, target: Message | MessageEvent) -> None:
    user_id = target_user_id(target)
    profile = await ctx.dialogs.get_profile(user_id)
    dialog = profile.active_dialog
    mode = dialog.mode if dialog is not None else profile.dialogs[0].mode
    await answer_screen(ctx, target, modes_text(mode), modes_keyboard(mode))


async def show_dialog_actions(
    ctx: AppContext,
    event: MessageEvent,
    dialog: Dialog,
) -> None:
    from keyboards.dialogs import dialog_actions_keyboard

    text = (
        f"Диалог «{dialog.title}»\n"
        f"Режим: {dialog.mode.label}\n"
        f"Сообщений: {dialog.message_count}\n\n"
        "Выберите действие."
    )
    await edit_event(event, text, dialog_actions_keyboard(dialog.id))


async def show_rag_status(
    ctx: AppContext,
    target: Message | MessageEvent,
) -> None:
    if not ctx.rag:
        await answer_screen(ctx, target, "RAG-контейнер отключён.", main_menu())
        return

    count = ctx.rag.chunk_count
    if count == 0:
        await answer_screen(
            ctx,
            target,
            "📚 База знаний пуста.\n\n"
            "Чтобы наполнить её:\n"
            "1. Положите файлы (.txt, .md, .pdf) в каталог data/rag/sources\n"
            "2. Запустите: python scripts/rag_index.py\n"
            "3. Перезапустите бота\n\n"
            "Или используйте CLI:\n"
            "  python scripts/rag_index.py --add <файл>\n"
            "  python scripts/rag_index.py --status",
            main_menu(),
        )
        return

    sources = {chunk.source for chunk in ctx.rag.chunks}
    await answer_screen(
        ctx,
        target,
        f"📚 База знаний\n\n"
        f"Чанков в индексе: {count}\n"
        f"Источников: {len(sources)}\n\n"
        "Бот отвечает на вопросы, опираясь на содержимое файлов.\n"
        "Чтобы обновить базу — запустите:\n"
        "  python scripts/rag_index.py\n\n"
        "Или добавьте файлы:\n"
        "  python scripts/rag_index.py --add <файл>",
        main_menu(),
    )
