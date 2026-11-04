"""Настройка логирования: консоль + ротация файла."""

from __future__ import annotations

import logging
import sys
from contextlib import suppress
from logging.handlers import RotatingFileHandler
from pathlib import Path

_NOISY_LOGGERS = (
    "vkbottle",
    "httpx",
    "httpcore",
    "mcp",
    "google_genai",
    "openai",
    "asyncio",
)


def configure_logging(level: str, log_file: Path) -> None:
    """Настроить корневой логгер и приглушить библиотечный шум."""
    for stream in (sys.stdout, sys.stderr):
        with suppress(Exception):
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    log_file.parent.mkdir(parents=True, exist_ok=True)
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=numeric_level,
        handlers=[console, file_handler],
        force=True,
    )

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(max(numeric_level, logging.WARNING))
