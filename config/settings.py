"""Конфигурация приложения из .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from utils.errors import ConfigError

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE, override=False)

_AI_PROVIDERS = frozenset({"gemini", "openai"})


def _str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None else value.strip()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name}: ожидается целое число") from exc


def _optional_int(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name}: ожидается целое число или пустое значение") from exc


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name}: ожидается число") from exc


def _path(name: str, default: str) -> Path:
    raw = _str(name, default) or default
    path = Path(raw).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


@dataclass(frozen=True, slots=True)
class Settings:
    """Все настройки бота, собранные из окружения."""

    vk_group_token: str
    vk_group_id: int | None
    proxy_api_key: str
    proxy_base_url: str

    ai_provider: str
    gemini_model: str
    gemini_fallback_model: str
    openai_model: str
    openai_fallback_model: str
    temperature: float
    max_output_tokens: int
    request_timeout: float

    embedding_model: str
    rag_top_k: int
    rag_enabled: bool

    mcp_host: str
    mcp_port: int
    mcp_path: str
    mcp_url: str
    mcp_timeout: float
    data_dir: Path

    history_limit: int
    history_max_chars: int
    max_dialogs: int
    max_message_chars: int

    log_level: str
    log_file: Path

    @property
    def primary_model(self) -> str:
        """Модель, которая используется первой."""
        return self.gemini_model if self.ai_provider == "gemini" else self.openai_model

    @property
    def fallback_model(self) -> str:
        """Модель на случай ошибки основной."""
        return (
            self.gemini_fallback_model
            if self.ai_provider == "gemini"
            else self.openai_fallback_model
        )


def load_settings() -> Settings:
    """Прочитать .env и вернуть валидированные настройки."""
    token = _str("VK_GROUP_TOKEN")
    if not token:
        raise ConfigError(
            "VK_GROUP_TOKEN не задан. Добавьте ключ доступа сообщества в .env."
        )

    proxy_key = _str("PROXY_API_KEY")
    if not proxy_key:
        raise ConfigError("PROXY_API_KEY не задан. Добавьте ключ ProxyAPI в .env.")

    provider = _str("AI_PROVIDER", "gemini").lower()
    if provider not in _AI_PROVIDERS:
        raise ConfigError(
            f"AI_PROVIDER={provider!r} не поддерживается. Допустимо: gemini, openai."
        )

    host = _str("MCP_HOST", "127.0.0.1")
    port = _int("MCP_PORT", 8765)
    path = _str("MCP_PATH", "/mcp")
    if not path.startswith("/"):
        path = "/" + path
    mcp_url = _str("MCP_URL") or f"http://{host}:{port}{path}"

    base_url = _str("PROXY_BASE_URL", "https://api.proxyapi.ru").rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    if base_url.endswith("/v1beta"):
        base_url = base_url[:-7]

    temperature = min(max(_float("TEMPERATURE", 0.6), 0.0), 2.0)
    max_output_tokens = max(64, _int("MAX_OUTPUT_TOKENS", 1200))
    history_limit = min(max(_int("HISTORY_LIMIT", 100), 2), 100)
    history_max_chars = max(1000, _int("HISTORY_MAX_CHARS", 14000))
    max_dialogs = min(max(_int("MAX_DIALOGS", 20), 1), 100)
    max_message_chars = min(max(_int("MAX_MESSAGE_CHARS", 3800), 500), 4000)

    embedding_model = _str("EMBEDDING_MODEL", "openai/text-embedding-3-small")
    rag_top_k = min(max(_int("RAG_TOP_K", 5), 1), 10)
    rag_enabled = _str("RAG_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

    return Settings(
        vk_group_token=token,
        vk_group_id=_optional_int("VK_GROUP_ID"),
        proxy_api_key=proxy_key,
        proxy_base_url=base_url,
        ai_provider=provider,
        gemini_model=_str("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        gemini_fallback_model=_str("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite"),
        openai_model=_str("OPENAI_MODEL", "openai/gpt-4.1-mini"),
        openai_fallback_model=_str("OPENAI_FALLBACK_MODEL", "deepseek/deepseek-chat"),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        request_timeout=max(5.0, _float("REQUEST_TIMEOUT", 90.0)),
        embedding_model=embedding_model,
        rag_top_k=rag_top_k,
        rag_enabled=rag_enabled,
        mcp_host=host,
        mcp_port=port,
        mcp_path=path,
        mcp_url=mcp_url,
        mcp_timeout=max(1.0, _float("MCP_TIMEOUT", 30.0)),
        data_dir=_path("DATA_DIR", "data/users"),
        history_limit=history_limit,
        history_max_chars=history_max_chars,
        max_dialogs=max_dialogs,
        max_message_chars=max_message_chars,
        log_level=_str("LOG_LEVEL", "INFO").upper(),
        log_file=_path("LOG_FILE", "data/bot.log"),
    )
