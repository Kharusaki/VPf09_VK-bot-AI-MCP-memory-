"""AI-сервис с резервной моделью.

Основная модель используется первой. Если она падает (сеть, лимит, ошибка
провайдера), сервис пробует резервную. Если не вышло ни разу — вызывающий
код получает AIUnavailableError и показывает пользователю понятный текст.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from config.settings import Settings
from utils.errors import AIUnavailableError

from .providers.base import AIProvider, AIProviderError, AIRequest
from .providers.gemini import GeminiProvider
from .providers.openai_compat import OpenAICompatProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AIResult:
    """Ответ модели вместе с информацией о том, кто его дал."""

    text: str
    model: str
    fallback_used: bool


class AIService:
    """Вызов модели с автоматическим переходом на резервную."""

    def __init__(
        self,
        settings: Settings,
        primary_provider: AIProvider | None = None,
        fallback_provider: AIProvider | None = None,
    ) -> None:
        self.primary_model = settings.primary_model
        self.fallback_model = settings.fallback_model
        self.temperature = settings.temperature
        self.max_output_tokens = settings.max_output_tokens
        self.timeout = settings.request_timeout

        if primary_provider is not None and fallback_provider is not None:
            self.primary_provider = primary_provider
            self.fallback_provider = fallback_provider
        else:
            provider = self._build_provider(settings)
            self.primary_provider = provider
            self.fallback_provider = provider

    @staticmethod
    def _build_provider(settings: Settings) -> AIProvider:
        if settings.ai_provider == "gemini":
            return GeminiProvider(
                api_key=settings.proxy_api_key,
                base_url=settings.proxy_base_url,
                timeout=settings.request_timeout,
            )
        return OpenAICompatProvider(
            api_key=settings.proxy_api_key,
            base_url=settings.proxy_base_url,
            timeout=settings.request_timeout,
        )

    async def generate(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> AIResult:
        """Получить ответ основной или резервной модели."""
        attempts = (
            (self.primary_provider, self.primary_model, False),
            (self.fallback_provider, self.fallback_model, True),
        )
        last_error: Exception | None = None

        for provider, model, is_fallback in attempts:
            request = AIRequest(
                model=model,
                system_prompt=system_prompt,
                messages=messages,
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
            )
            try:
                text = await asyncio.wait_for(
                    provider.generate(request), timeout=self.timeout
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Модель %s не ответила (%s): %s",
                    model,
                    "резервная" if is_fallback else "основная",
                    exc,
                )
                continue

            text = text.strip()
            if not text:
                last_error = AIProviderError("Модель вернула пустой ответ")
                continue

            return AIResult(text=text, model=model, fallback_used=is_fallback)

        logger.error("Все AI-модели недоступны: %s", last_error)
        raise AIUnavailableError(
            "Не удалось получить ответ ни от основной, ни от резервной модели"
        ) from last_error
