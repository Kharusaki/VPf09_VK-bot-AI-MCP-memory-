"""Общие фикстуры и фабрики для тестов."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from config.settings import Settings


def make_settings(**overrides: Any) -> Settings:
    """Собрать Settings без чтения .env и секретов."""
    values: dict[str, Any] = {
        "vk_group_token": "test-vk-token",
        "vk_group_id": 1,
        "proxy_api_key": "test-proxy-key",
        "proxy_base_url": "https://api.proxyapi.ru",
        "ai_provider": "openai",
        "gemini_model": "gemini-test",
        "gemini_fallback_model": "gemini-test-fallback",
        "openai_model": "openai/test",
        "openai_fallback_model": "openai/test-fallback",
        "temperature": 0.6,
        "max_output_tokens": 256,
        "request_timeout": 5.0,
        "embedding_model": "openai/text-embedding-3-small",
        "rag_top_k": 5,
        "rag_enabled": True,
        "mcp_host": "127.0.0.1",
        "mcp_port": 8765,
        "mcp_path": "/mcp",
        "mcp_url": "http://127.0.0.1:8765/mcp",
        "mcp_timeout": 5.0,
        "data_dir": Path("data/users"),
        "history_limit": 100,
        "history_max_chars": 14_000,
        "max_dialogs": 20,
        "max_message_chars": 3_800,
        "log_level": "INFO",
        "log_file": Path("data/bot.log"),
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture()
def settings() -> Settings:
    return make_settings()


__all__ = ("make_settings", "settings")
