"""Экземпляр FastMCP и общие зависимости инструментов."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import load_server_settings
from .json_store import JsonUserStore
from .repository import UserRepository

settings = load_server_settings()
store = JsonUserStore(settings.data_dir, settings.max_file_bytes)
repository = UserRepository(store)

# stateless_http + json_response: сервер не хранит сессии, ответы идут обычным
# JSON. Для локального бота это проще и надёжнее, чем SSE-сессии.
mcp = FastMCP(
    "vk-assistant-storage",
    instructions=(
        "Хранилище профилей VK AI-ассистента. Профиль пользователя содержит "
        "диалоги, историю сообщений и выбранный режим. Читайте и сохраняйте "
        "профиль целиком через инструменты get_user и save_user."
    ),
    host=settings.host,
    port=settings.port,
    streamable_http_path=settings.path,
    json_response=True,
    stateless_http=True,
)
