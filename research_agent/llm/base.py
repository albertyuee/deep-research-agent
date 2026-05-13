from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send messages and return the full response."""
        ...

    @abstractmethod
    async def stream_chat(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """Send messages and yield response chunks."""
        ...

    @abstractmethod
    async def chat_structured(
        self, messages: list[dict], output_schema: dict, **kwargs
    ) -> dict:
        """Send messages and return structured JSON output."""
        ...
