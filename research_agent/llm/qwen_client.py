from __future__ import annotations

import json
from typing import AsyncIterator

from openai import AsyncOpenAI

from research_agent.llm.base import BaseLLMClient


class QwenClient(BaseLLMClient):
    """Qwen (通义千问) LLM client via OpenAI-compatible API."""

    def __init__(self, model: str, api_key: str, base_url: str, **kwargs):
        self.model = model
        self.temperature = kwargs.get("temperature", 0.3)
        self.max_tokens = kwargs.get("max_tokens", 4096)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

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
        """Use JSON mode for structured output."""
        schema_prompt = (
            f"\n请以 JSON 格式返回结果，严格遵循以下 schema：\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}\n"
            f"只返回 JSON，不要包含其他内容。"
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
