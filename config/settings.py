from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field


ENV_FILE = Path(__file__).parent / ".env"


def load_env() -> None:
    """Load .env and sync LangSmith aliases before tracing decorators run."""
    load_dotenv(ENV_FILE, override=True)
    if os.getenv("LANGSMITH_API_KEY") and not os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]
    if os.getenv("LANGSMITH_PROJECT") and not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = os.environ["LANGSMITH_PROJECT"]
    if os.getenv("LANGSMITH_TRACING") and not os.getenv("LANGSMITH_TRACING_V2"):
        os.environ["LANGSMITH_TRACING_V2"] = os.environ["LANGSMITH_TRACING"]
    if os.getenv("LANGSMITH_TRACING_V2") and not os.getenv("LANGCHAIN_TRACING_V2"):
        os.environ["LANGCHAIN_TRACING_V2"] = os.environ["LANGSMITH_TRACING_V2"]
    if os.getenv("LANGSMITH_ENDPOINT") and not os.getenv("LANGCHAIN_ENDPOINT"):
        os.environ["LANGCHAIN_ENDPOINT"] = os.environ["LANGSMITH_ENDPOINT"]


load_env()


class LLMSettings(BaseSettings):
    model_config = {
        "env_prefix": "LLM_",
        "env_file": ENV_FILE,
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
    query_max_chars: int = 500
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
    max_top_k: int = 20
    max_concurrency: int = 2
    max_retries: int = 3
    critique_threshold: float = 0.6
    rrf_k: int = 60
    vector_backend: Literal["milvus", "chroma"] = "chroma"


class ReasoningSettings(BaseSettings):
    model_config = {
        "env_prefix": "REASONING_",
        "env_file": ENV_FILE,
        "extra": "ignore",
    }

    enabled: bool = True
    max_sub_queries: int = 3
    max_hops: int = 3
    context_max_chars: int = 3000
    search_query_max_chars: int = 400


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


class LangSmithSettings(BaseSettings):
    model_config = {
        "env_prefix": "LANGSMITH_",
        "env_file": ENV_FILE,
        "extra": "ignore"
    }

    tracing: bool = False
    tracing_v2: bool = False
    api_key: str = ""
    project: str = "deep-research-agent"
    endpoint: str = "https://api.smith.langchain.com"


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
    reasoning: ReasoningSettings = Field(default_factory=ReasoningSettings)
    rerank: RerankSettings = Field(default_factory=RerankSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    langsmith: LangSmithSettings = Field(default_factory=LangSmithSettings)

    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")


settings = Settings()


def reload_settings():
    """Reload settings in place so imported references see new values."""
    load_env()
    refreshed = Settings()
    for field_name in Settings.model_fields:
        setattr(settings, field_name, getattr(refreshed, field_name))
    return settings
