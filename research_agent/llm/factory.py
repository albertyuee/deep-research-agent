from __future__ import annotations

from research_agent.llm.base import BaseLLMClient
from research_agent.llm.openai_client import OpenAIClient
from research_agent.llm.qwen_client import QwenClient
from config.settings import settings


_PROVIDER_MAP = {
    "qwen": QwenClient,
    "openai": OpenAIClient,
    "siliconflow": OpenAIClient,  # SiliconFlow uses OpenAI-compatible API
}

_DEFAULT_BASE_URLS = {
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
}

_DEFAULT_MODELS = {
    "siliconflow": "Qwen/Qwen3-8B",
    "qwen": "qwen-plus",
    "openai": "gpt-4o-mini",
}


def create_llm_client() -> BaseLLMClient:
    """Create an LLM client from settings."""
    cfg = settings.llm
    client_cls = _PROVIDER_MAP.get(cfg.provider, OpenAIClient)

    base_url = cfg.base_url or _DEFAULT_BASE_URLS.get(cfg.provider, "")
    model = cfg.model or _DEFAULT_MODELS.get(cfg.provider, "gpt-4o-mini")

    return client_cls(
        model=model,
        api_key=cfg.api_key,
        base_url=base_url,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )
