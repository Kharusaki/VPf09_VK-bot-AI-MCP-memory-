"""Провайдер OpenAI-совместимого API ProxyAPI.

Используется на этапе настройки: дешёвая модель и полные имена каталога
ProxyAPI (например, openai/gpt-4.1-mini).
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from .base import AIProvider, AIProviderError, AIRequest

logger = logging.getLogger(__name__)


class OpenAICompatProvider(AIProvider):
    """OpenAI SDK, направленный на https://api.proxyapi.ru/v1."""

    name = "openai"

    def __init__(self, api_key: str, base_url: str, timeout: float = 90.0) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=f"{base_url.rstrip('/')}/v1",
            timeout=max(5.0, timeout),
            max_retries=0,
        )

    async def generate(self, request: AIRequest) -> str:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": request.system_prompt}
        ]
        messages.extend(
            {"role": message["role"], "content": message["content"]}
            for message in request.messages
            if message.get("content")
        )

        try:
            response = await self._client.chat.completions.create(
                model=request.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=request.temperature,
                max_tokens=request.max_output_tokens,
            )
        except Exception as exc:
            logger.warning("OpenAI-совместимая модель (%s): %s", request.model, exc)
            raise AIProviderError(f"Модель недоступна: {exc}") from exc

        if not response.choices:
            raise AIProviderError("Модель вернула пустой список вариантов")
        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise AIProviderError("Модель вернула пустой ответ")
        return text
