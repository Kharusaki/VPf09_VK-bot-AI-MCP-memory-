"""Общий интерфейс AI-провайдеров."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class AIProviderError(RuntimeError):
    """Провайдер не смог получить ответ."""


@dataclass(frozen=True, slots=True)
class AIRequest:
    """Запрос к модели, не зависящий от конкретного SDK."""

    model: str
    system_prompt: str
    messages: list[dict[str, str]]
    temperature: float
    max_output_tokens: int


class AIProvider(ABC):
    """Базовый класс провайдера."""

    name: str

    @abstractmethod
    async def generate(self, request: AIRequest) -> str:
        """Вернуть текст ответа модели."""
        raise NotImplementedError
