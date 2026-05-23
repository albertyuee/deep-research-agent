from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings
from pydantic import Field


class LLMSettings(BaseSettings):
    model_config = {
        "env_prefix": "LLM_",
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    provider: Literal["qwen", "openai", "siliconflow"] = "siliconflow"
    model: str = "Qwen/Qwen3-8B"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096


class EmbeddingSettings(BaseSettings):
    model_config = {
        "env_prefix": "EMBEDDING_",
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    mode: Literal["local", "api"] = "local"
    model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str = "cpu"
    dimension: int = 384
    api_base_url: str = "https://api.siliconflow.cn/v1"
    api_key: str = ""


class MilvusSettings(BaseSettings):
    model_config = {
        "env_prefix": "MILVUS_",
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    # Self-hosted Milvus
    host: str = "localhost"
    port: int = 19530
    # Zilliz Cloud (managed Milvus) — set uri + token instead of host/port
    uri: str = ""
    token: str = ""
    # Common
    collection_name: str = "research_docs"
    dimension: int = 384


class ChromaSettings(BaseSettings):
    model_config = {
        "env_prefix": "CHROMA_",
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    persist_dir: str = "./data/chroma_db"
    collection_name: str = "research_docs"

    @property
    def resolved_persist_dir(self) -> Path:
        p = Path(self.persist_dir)
        if not p.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            p = project_root / p
        return p.resolve()


class RetrievalSettings(BaseSettings):
    model_config = {
        "env_prefix": "RETRIEVAL_",
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    top_k: int = 5
    retry_top_k_multiplier: int = 2
    max_retries: int = 3
    critique_threshold: float = 0.6
    rrf_k: int = 60
    vector_backend: Literal["milvus", "chroma"] = "chroma"


class RerankSettings(BaseSettings):
    model_config = {
        "env_prefix": "RERANK_",
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    enabled: bool = False
    provider: Literal["siliconflow"] = "siliconflow"
    model: str = "Qwen/Qwen3-Reranker-8B"
    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"
    instruction: str = "请根据查询内容判断文档与查询的相关性，并按相关性从高到低排序。"
    top_n: int = 5
    candidate_multiplier: int = 4
    timeout: float = 30.0


class MCPSettings(BaseSettings):
    model_config = {
        "env_prefix": "MCP_",
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    web_search_enabled: bool = False
    tavily_api_key: str = ""
    tavily_max_results: int = 5
    web_search_timeout: float = 30.0


class Settings(BaseSettings):
    model_config = {
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    rerank: RerankSettings = Field(default_factory=RerankSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)

    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")


settings = Settings()


def reload_settings():
    """Reload settings from .env after changes. Rebuild the singleton."""
    global settings
    settings = Settings()
