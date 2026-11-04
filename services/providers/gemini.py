"""Провайдер Gemini через нативный API ProxyAPI."""

from __future__ import annotations

import logging

from google import genai
from google.genai import types

from .base import AIProvider, AIProviderError, AIRequest

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Google GenAI SDK с базовым URL ProxyAPI (/v1beta)."""

    name = "gemini"

    def __init__(self, api_key: str, base_url: str, timeout: float = 90.0) -> None:
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                base_url=base_url,
                api_version="v1beta",
                timeout=int(max(1.0, timeout) * 1000),
            ),
        )

    async def generate(self, request: AIRequest) -> str:
        contents = [
            types.Content(
                role="user" if message["role"] == "user" else "model",
                parts=[types.Part(text=message["content"])],
            )
            for message in request.messages
            if message.get("content")
        ]
        if not contents:
            raise AIProviderError("Пустой контекст для Gemini")

        config = types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=request.model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            logger.warning("Gemini (%s) вернул ошибку: %s", request.model, exc)
            raise AIProviderError(f"Gemini недоступен: {exc}") from exc

        text = (getattr(response, "text", None) or "").strip()
        if not text:
            feedback = getattr(response, "prompt_feedback", None)
            raise AIProviderError(f"Gemini вернул пустой ответ ({feedback})")
        return text
