"""Постоянная MCP-сессия поверх Streamable HTTP.

MCP SDK использует anyio cancel scopes, которые обязаны открываться и
закрываться в одной и той же задаче. Поэтому соединение живёт в отдельной
задаче-акторе, а остальной код общается с ней через asyncio.Queue.

Актор сам переподключается после обрыва: один неудачный вызов не ломает
бота, следующие запросы обслуживаются новой сессией.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from utils.errors import StorageError

logger = logging.getLogger(__name__)

_QueueItem = tuple[str, dict[str, Any], "asyncio.Future[dict[str, Any]]"]


class MCPStorageClient:
    """Клиент MCP-хранилища с автоматическим переподключением."""

    def __init__(
        self,
        url: str,
        timeout: float = 30.0,
        connect_timeout: float = 5.0,
        retry_delay: float = 1.0,
    ) -> None:
        self.url = url
        self.timeout = max(1.0, float(timeout))
        self.connect_timeout = max(1.0, float(connect_timeout))
        self.retry_delay = max(0.2, float(retry_delay))

        self._queue: asyncio.Queue[_QueueItem | None] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._connected = asyncio.Event()
        self._last_error: Exception | None = None
        self._stopping = False

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    async def start(self) -> None:
        """Запустить задачу-актор и подождать первое подключение."""
        if self._task is not None and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(self._actor(), name="mcp-storage-actor")
        try:
            await asyncio.wait_for(
                self._connected.wait(), timeout=self.connect_timeout
            )
        except TimeoutError:
            logger.warning(
                "MCP-хранилище пока недоступно (%s). Клиент продолжит попытки.",
                self.url,
            )

    async def stop(self) -> None:
        """Остановить актор и закрыть сессию."""
        self._stopping = True
        task = self._task
        self._task = None
        if task is not None and not task.done():
            await self._queue.put(None)
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except TimeoutError:
                task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await task
        self._connected.clear()
        self._fail_pending(StorageError("MCP-клиент остановлен"))

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        wait_timeout: float | None = None,
    ) -> dict[str, Any]:
        """Вызвать MCP-инструмент и вернуть разобранный JSON-ответ."""
        if self._task is None or self._task.done():
            await self.start()

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        await self._queue.put((name, arguments, future))

        try:
            return await asyncio.wait_for(
                future, timeout=self.timeout if wait_timeout is None else wait_timeout
            )
        except TimeoutError as exc:
            future.cancel()
            raise StorageError(
                f"MCP-инструмент {name} не ответил за отведённое время"
            ) from exc

    async def ping(self) -> dict[str, Any]:
        """Проверить соединение с сервером."""
        return await self.call_tool("ping", {}, wait_timeout=self.connect_timeout)

    async def _actor(self) -> None:
        """Держать одну сессию и обслуживать очередь вызовов."""
        while True:
            try:
                async with self._session() as session:
                    self._last_error = None
                    self._connected.set()
                    logger.info("MCP-сессия открыта: %s", self.url)
                    while True:
                        item = await self._queue.get()
                        if item is None:
                            logger.info("MCP-клиент получил команду остановки")
                            return
                        name, arguments, future = item
                        if future.done():
                            continue
                        try:
                            payload = await self._invoke(session, name, arguments)
                        except asyncio.CancelledError:
                            if not future.done():
                                future.cancel()
                            raise
                        except Exception as exc:
                            if not future.done():
                                future.set_exception(
                                    StorageError(
                                        f"Ошибка MCP-инструмента {name}: {exc}"
                                    )
                                )
                            self._last_error = exc
                            logger.warning(
                                "MCP-вызов %s сорвался, переподключаюсь: %s",
                                name,
                                exc,
                            )
                            break
                        else:
                            if not future.done():
                                future.set_result(payload)
            except asyncio.CancelledError:
                self._connected.clear()
                self._fail_pending(StorageError("MCP-клиент остановлен"))
                raise
            except Exception as exc:
                self._connected.clear()
                self._last_error = exc
                logger.warning(
                    "MCP-сессия недоступна (%s): %s. Повтор через %.1f с.",
                    self.url,
                    exc,
                    self.retry_delay,
                )
                try:
                    await asyncio.sleep(self.retry_delay)
                except asyncio.CancelledError:
                    self._fail_pending(StorageError("MCP-клиент остановлен"))
                    raise

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        """Открыть MCP-сессию и корректно закрыть её в этой же задаче."""
        stack = AsyncExitStack()
        try:
            http_client = await stack.enter_async_context(
                httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout, read=self.timeout),
                    follow_redirects=True,
                    # MCP-хранилище живёт на localhost: системный HTTP_PROXY
                    # (например, локальный прокси) разрывает стриминг SSE,
                    # поэтому соединение идёт напрямую, в обход переменных окружения.
                    trust_env=False,
                )
            )
            read_stream, write_stream, _ = await stack.enter_async_context(
                streamable_http_client(self.url, http_client=http_client)
            )
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
        except BaseException:
            with suppress(Exception):
                await stack.aclose()
            raise

        try:
            yield session
        finally:
            with suppress(Exception):
                await stack.aclose()

    async def _invoke(
        self,
        session: ClientSession,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        result = await session.call_tool(name, arguments)
        return self._parse_result(result)

    @staticmethod
    def _parse_result(result: Any) -> dict[str, Any]:
        """Разобрать CallToolResult в обычный словарь."""
        text_parts = [
            str(item.text)
            for item in (getattr(result, "content", None) or [])
            if getattr(item, "text", None)
        ]
        text = "\n".join(text_parts).strip()

        payload: Any = None
        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, dict):
            payload = structured
            if set(payload) == {"result"} and isinstance(payload["result"], dict):
                payload = payload["result"]

        if payload is None and text:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = None

        if getattr(result, "isError", False):
            message = text or "MCP-инструмент завершился с ошибкой"
            raise StorageError(message)

        if not isinstance(payload, dict):
            return {"ok": True, "value": payload if payload is not None else text}

        if payload.get("ok") is False:
            raise StorageError(str(payload.get("error") or "Ошибка MCP-хранилища"))
        return payload

    def _fail_pending(self, error: Exception) -> None:
        """Завершить ожидающие вызовы понятной ошибкой."""
        while True:
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            if item is None:
                continue
            _name, _arguments, future = item
            if not future.done():
                future.set_exception(error)
