from __future__ import annotations

import json
from typing import AsyncIterator

from openai import AsyncOpenAI

from research_agent.llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """OpenAI-compatible LLM client."""

    def __init__(self, model: str, api_key: str, base_url: str = "", **kwargs):
        self.model = model
        self.temperature = kwargs.get("temperature", 0.3)
        self.max_tokens = kwargs.get("max_tokens", 4096)
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**client_kwargs)

    async def chat(self, messages: list[dict], **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return response.choices[0].message.content or ""

    async def stream_chat(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def chat_structured(
        self, messages: list[dict], output_schema: dict, **kwargs
    ) -> dict:
        schema_prompt = (
            f"\nRespond in JSON format following this schema:\n{json.dumps(output_schema, indent=2)}\n"
            f"Return ONLY the JSON object, no other text."
        )
        messages[-1]["content"] += schema_prompt

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
