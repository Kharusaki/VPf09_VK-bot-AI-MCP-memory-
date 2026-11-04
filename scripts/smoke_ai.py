"""Проверка AI-подключения без запуска VK-бота.

Скрипт делает один запрос к основной модели и печатает ответ. Если основная
модель недоступна, AI-сервис автоматически пробует резервную.

Примеры:
    python scripts/smoke_ai.py
    python scripts/smoke_ai.py --provider gemini
    python scripts/smoke_ai.py --provider openai --model openai/gpt-4.1-mini
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import replace
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.prompts import build_system_prompt  # noqa: E402
from config.settings import load_settings  # noqa: E402
from models.enums import Mode  # noqa: E402
from services.ai_service import AIService  # noqa: E402
from utils.errors import AIUnavailableError, ConfigError  # noqa: E402
from utils.logging import configure_logging  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Проверка подключения к AI через ProxyAPI")
    parser.add_argument(
        "--provider",
        choices=("openai", "gemini"),
        help="Провайдер: openai (дешёвая настройка) или gemini (финальный режим)",
    )
    parser.add_argument("--model", help="Переопределить основную модель")
    parser.add_argument(
        "--prompt",
        default="Ответь одним коротким предложением: подключение к AI работает?",
        help="Текст тестового запроса",
    )
    return parser.parse_args()


async def _run() -> int:
    args = _parse_args()
    settings = load_settings()
    configure_logging(settings.log_level, settings.log_file)

    if args.provider:
        settings = replace(settings, ai_provider=args.provider)
    if args.model:
        field = "gemini_model" if settings.ai_provider == "gemini" else "openai_model"
        settings = replace(settings, **{field: args.model})

    service = AIService(settings=settings)
    print(f"Провайдер: {settings.ai_provider}")
    print(f"Основная модель: {settings.primary_model}")
    print(f"Резервная модель: {settings.fallback_model}")
    print("Отправляю тестовый запрос…\n")

    try:
        result = await service.generate(
            system_prompt=build_system_prompt(Mode.ASSISTANT),
            messages=[{"role": "user", "content": args.prompt}],
        )
    except AIUnavailableError as exc:
        print(f"ОШИБКА: ни одна модель не ответила. {exc}")
        return 1

    print(f"Модель ответа: {result.model}")
    print(f"Использована резервная: {'да' if result.fallback_used else 'нет'}")
    print(f"Ответ:\n{result.text}")
    return 0


def main() -> None:
    try:
        code = asyncio.run(_run())
    except ConfigError as exc:
        print(f"ОШИБКА КОНФИГУРАЦИИ: {exc}")
        code = 2
    except KeyboardInterrupt:
        code = 130
    raise SystemExit(code)


if __name__ == "__main__":
    main()
