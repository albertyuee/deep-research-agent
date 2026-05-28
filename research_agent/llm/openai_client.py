from __future__ import annotations

import asyncio
import json
import logging
import traceback
from typing import AsyncIterator

import httpx
from langsmith import traceable

from research_agent.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120.0
DEFAULT_MAX_RETRIES = 1


class OpenAIClient(BaseLLMClient):
    """OpenAI-compatible LLM client using httpx.AsyncClient directly."""

    def __init__(self, model: str, api_key: str, base_url: str = "", **kwargs):
        self.model = model
        self.temperature = kwargs.get("temperature", 0.3)
        self.max_tokens = kwargs.get("max_tokens", 4096)
        self.timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)
        self.max_retries = kwargs.get("max_retries", DEFAULT_MAX_RETRIES)
        self.base_url = (base_url.rstrip("/") if base_url else "https://api.openai.com/v1")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_body(self, messages: list[dict], **kwargs) -> dict:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        if "response_format" in kwargs:
            body["response_format"] = kwargs["response_format"]
        return body

    async def _post(self, body: dict) -> dict:
        """Make async API call, return parsed JSON."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=30.0)) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers=self._headers(),
            )
            if resp.status_code != 200:
                body_preview = resp.text[:500]
                logger.error(
                    f"API returned non-200 status {resp.status_code}. Response body: {body_preview}"
                )
                raise RuntimeError(f"API error {resp.status_code}: {body_preview}")
            return resp.json()

    async def _retry(self, fn, label: str):
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await fn()
            except Exception as e:
                last_error = e
                tb = traceback.format_exc()
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    logger.warning(
                        f"LLM {label} attempt {attempt+1} failed: {type(e).__name__}: {e}\n"
                        f"Traceback:\n{tb}\n"
                        f"Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        f"LLM {label} all attempts exhausted. "
                        f"Exception: {type(e).__name__}: {e}\n"
                        f"Traceback:\n{tb}"
                    )
        raise last_error

    @traceable(name="openai_chat", run_type="llm")
    async def chat(self, messages: list[dict], **kwargs) -> str:
        body = self._build_body(messages, **kwargs)

        async def _fn():
            data = await self._post(body)
            logger.debug(f"[openai_client] raw API response: {json.dumps(data, ensure_ascii=False)[:500]}")
            if "choices" not in data or not data["choices"]:
                raise RuntimeError(f"Unexpected API response — no choices in data: {json.dumps(data, ensure_ascii=False)[:300]}")
            return data["choices"][0]["message"]["content"] or ""

        return await self._retry(_fn, "chat")

    @traceable(name="openai_stream_chat", run_type="llm", reduce_fn=lambda chunks: "".join(chunks))
    async def stream_chat(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        body = self._build_body(messages, **kwargs)
        body["stream"] = True

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=30.0)) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=body,
                headers=self._headers(),
            ) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"API error {resp.status_code}")
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            d = json.loads(data_str)
                            choices = d.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            pass

    @traceable(name="openai_chat_structured", run_type="llm")
    async def chat_structured(
        self, messages: list[dict], output_schema: dict, **kwargs
    ) -> dict:
        user_msg = dict(messages[-1])
        user_msg["content"] = user_msg.get("content", "") + (
            f"\nRespond in JSON format following this schema:\n"
            f"{json.dumps(output_schema, indent=2)}\n"
            f"Return ONLY the JSON object, no other text."
        )
        msgs = messages[:-1] + [user_msg]
        body = self._build_body(
            msgs, response_format={"type": "json_object"}, temperature=0.1, **kwargs
        )

        async def _fn():
            data = await self._post(body)
            logger.debug(f"[openai_client] raw API response: {json.dumps(data, ensure_ascii=False)[:500]}")
            if "choices" not in data or not data["choices"]:
                raise RuntimeError(f"Unexpected API response — no choices in data: {json.dumps(data, ensure_ascii=False)[:300]}")
            content = data["choices"][0]["message"]["content"] or "{}"
            return json.loads(content)

        return await self._retry(_fn, "chat_structured")
