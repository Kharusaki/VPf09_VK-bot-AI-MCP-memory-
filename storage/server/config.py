"""Настройки MCP-сервера хранилища.

Сервер запускается отдельным процессом и не должен зависеть от VK-токена,
поэтому конфигурация читается здесь, а не из config.settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE, override=False)


def _str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None else value.strip()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _path(name: str, default: str) -> Path:
    raw = _str(name, default) or default
    path = Path(raw).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


@dataclass(frozen=True, slots=True)
class ServerSettings:
    """Параметры HTTP-транспорта и каталога с JSON-файлами."""

    host: str
    port: int
    path: str
    data_dir: Path
    max_file_bytes: int
    log_level: str

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{self.path}"


def load_server_settings() -> ServerSettings:
    """Собрать настройки MCP-сервера из окружения."""
    host = _str("MCP_HOST", "127.0.0.1")
    port = _int("MCP_PORT", 8765)
    path = _str("MCP_PATH", "/mcp")
    if not path.startswith("/"):
        path = "/" + path

    return ServerSettings(
        host=host,
        port=port,
        path=path,
        data_dir=_path("DATA_DIR", "data/users"),
        max_file_bytes=max(10_000, _int("MAX_USER_FILE_BYTES", 5_000_000)),
        log_level=_str("LOG_LEVEL", "INFO").upper(),
    )
