"""Отправка сообщений во ВКонтакте.

Сервис инкапсулирует ограничения VK: длинные ответы делятся на части,
«печатает…» включается отдельным методом, а сообщение-заглушка «🤔 Думаю…»
редактируется в готовый ответ. Все ошибки VK API логируются, но не роняют
обработчик целиком.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from config.settings import Settings
from utils.text import split_text

logger = logging.getLogger(__name__)


class MessagingService:
    """Обёртка над messages.* API."""

    def __init__(self, api: Any, settings: Settings) -> None:
        self.api = api
        self.group_id = settings.vk_group_id
        self.max_chars = settings.max_message_chars

    async def typing(self, peer_id: int) -> None:
        """Показать «печатает…». Ошибка не должна ломать ответ."""
        payload: dict[str, Any] = {"peer_id": peer_id, "type": "typing"}
        if self.group_id:
            payload["group_id"] = self.group_id
        try:
            await self.api.request("messages.setActivity", payload)
        except Exception as exc:
            logger.debug("Не удалось включить typing для %s: %s", peer_id, exc)

    async def send(
        self,
        peer_id: int,
        text: str,
        keyboard: Any | None = None,
    ) -> int | None:
        """Отправить одно сообщение и вернуть message_id."""
        payload: dict[str, Any] = {
            "peer_id": peer_id,
            "message": text,
            "random_id": random.getrandbits(31),
        }
        if keyboard is not None:
            payload["keyboard"] = keyboard.get_json()
        if self.group_id:
            payload["group_id"] = self.group_id

        try:
            response = await self.api.messages.send(**payload)
        except Exception as exc:
            logger.exception("Не удалось отправить сообщение %s: %s", peer_id, exc)
            return None
        return self._message_id(response)

    async def send_long(
        self,
        peer_id: int,
        text: str,
        keyboard: Any | None = None,
    ) -> list[int]:
        """Отправить длинный текст несколькими сообщениями."""
        chunks = split_text(text, self.max_chars)
        if not chunks:
            return []

        message_ids: list[int] = []
        for index, chunk in enumerate(chunks):
            message_id = await self.send(
                peer_id,
                chunk,
                keyboard=keyboard if index == 0 else None,
            )
            if message_id is not None:
                message_ids.append(message_id)
            if index < len(chunks) - 1:
                await asyncio.sleep(0.25)
        return message_ids

    async def send_placeholder(self, peer_id: int) -> int | None:
        """Отправить «🤔 Думаю…», чтобы пользователь видел прогресс."""
        return await self.send(peer_id, "🤔 Думаю…")

    async def edit(
        self,
        peer_id: int,
        message_id: int,
        text: str,
        keyboard: Any | None = None,
    ) -> bool:
        """Отредактировать сообщение. False — если VK не разрешил."""
        payload: dict[str, Any] = {
            "peer_id": peer_id,
            "message_id": message_id,
            "message": text,
        }
        if keyboard is not None:
            payload["keyboard"] = keyboard.get_json()

        try:
            await self.api.request("messages.edit", payload)
            return True
        except Exception as exc:
            logger.warning("Не удалось отредактировать сообщение %s: %s", message_id, exc)
            return False

    async def replace_placeholder(
        self,
        peer_id: int,
        message_id: int | None,
        text: str,
        keyboard: Any | None = None,
    ) -> list[int]:
        """Заменить заглушку готовым ответом, разбив длинный текст."""
        chunks = split_text(text, self.max_chars)
        if not chunks:
            chunks = ["Готово."]

        if message_id is not None and await self.edit(
            peer_id, message_id, chunks[0], keyboard
        ):
            first_id = message_id
        else:
            first_id = await self.send(peer_id, chunks[0], keyboard)

        message_ids = [first_id] if first_id is not None else []
        for chunk in chunks[1:]:
            await asyncio.sleep(0.25)
            extra_id = await self.send(peer_id, chunk)
            if extra_id is not None:
                message_ids.append(extra_id)
        return message_ids

    async def edit_keyboard(
        self,
        peer_id: int,
        message_id: int,
        text: str,
        keyboard: Any | None,
    ) -> bool:
        """Обновить текст и клавиатуру существующего сообщения."""
        return await self.edit(peer_id, message_id, text, keyboard)

    @staticmethod
    def _message_id(response: Any) -> int | None:
        if isinstance(response, int):
            return response
        if isinstance(response, list) and response:
            first = response[0]
            value = getattr(first, "message_id", None)
            if isinstance(value, int):
                return value
        return None
