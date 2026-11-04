"""Тесты AI-сервиса: основная модель, резервная и полный отказ."""

from __future__ import annotations

import pytest

from services.ai_service import AIService
from services.providers.base import AIProvider, AIProviderError, AIRequest
from utils.errors import AIUnavailableError

from .conftest import make_settings


class FakeProvider(AIProvider):
    name = "fake"

    def __init__(self, result: str | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.requests: list[AIRequest] = []

    async def generate(self, request: AIRequest) -> str:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result or ""


def _service(primary: FakeProvider, fallback: FakeProvider) -> AIService:
    return AIService(
        settings=make_settings(
            ai_provider="openai",
            openai_model="primary-model",
            openai_fallback_model="fallback-model",
            request_timeout=2.0,
        ),
        primary_provider=primary,
        fallback_provider=fallback,
    )


async def test_primary_model_success_does_not_call_fallback() -> None:
    primary = FakeProvider("Ответ основной модели")
    fallback = FakeProvider("Ответ резервной модели")
    service = _service(primary, fallback)

    result = await service.generate("system", [{"role": "user", "content": "Привет"}])

    assert result.text == "Ответ основной модели"
    assert result.model == "primary-model"
    assert result.fallback_used is False
    assert len(primary.requests) == 1
    assert fallback.requests == []
    assert primary.requests[0].model == "primary-model"
    assert primary.requests[0].messages == [{"role": "user", "content": "Привет"}]


async def test_primary_error_switches_to_fallback() -> None:
    primary = FakeProvider(error=AIProviderError("сеть недоступна"))
    fallback = FakeProvider("Ответ резервной модели")
    service = _service(primary, fallback)

    result = await service.generate("system", [{"role": "user", "content": "Привет"}])

    assert result.text == "Ответ резервной модели"
    assert result.model == "fallback-model"
    assert result.fallback_used is True
    assert fallback.requests[0].model == "fallback-model"


async def test_empty_primary_response_switches_to_fallback() -> None:
    primary = FakeProvider("   ")
    fallback = FakeProvider("Нормальный ответ")
    service = _service(primary, fallback)

    result = await service.generate("system", [{"role": "user", "content": "Привет"}])

    assert result.text == "Нормальный ответ"
    assert result.fallback_used is True


async def test_both_models_fail_raises_ai_unavailable() -> None:
    primary = FakeProvider(error=AIProviderError("primary down"))
    fallback = FakeProvider(error=AIProviderError("fallback down"))
    service = _service(primary, fallback)

    with pytest.raises(AIUnavailableError):
        await service.generate("system", [{"role": "user", "content": "Привет"}])


async def test_empty_fallback_response_raises_ai_unavailable() -> None:
    primary = FakeProvider(error=AIProviderError("primary down"))
    fallback = FakeProvider("")
    service = _service(primary, fallback)

    with pytest.raises(AIUnavailableError):
        await service.generate("system", [{"role": "user", "content": "Привет"}])


async def test_request_passes_generation_options() -> None:
    primary = FakeProvider("ok")
    fallback = FakeProvider("ok")
    service = _service(primary, fallback)

    await service.generate("системная инструкция", [{"role": "user", "content": "вопрос"}])

    request = primary.requests[0]
    assert request.system_prompt == "системная инструкция"
    assert request.temperature == 0.6
    assert request.max_output_tokens == 256
