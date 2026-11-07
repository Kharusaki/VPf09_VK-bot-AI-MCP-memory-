"""Запуск MCP-сервера по транспорту Streamable HTTP."""

from __future__ import annotations

import logging

from . import tools  # noqa: F401  # импорт регистрирует инструменты в FastMCP
from .app import lead_store, mcp, questionnaire_store, settings, store

logger = logging.getLogger(__name__)


def main() -> None:
    """Подготовить каталог данных и запустить сервер до остановки процесса."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    store.ensure_ready()
    questionnaire_store.ensure_ready()
    lead_store.ensure_ready()
    logger.info("MCP-хранилище запускается: %s", settings.url)
    logger.info("Каталог данных: %s", settings.data_dir)
    logger.info("Каталог анкет: %s", settings.questionnaire_dir)
    logger.info("Каталог заявок: %s", settings.lead_dir)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
