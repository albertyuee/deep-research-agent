from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings
from pydantic import Field


class LLMSettings(BaseSettings):
    model_config = {"env_prefix": "LLM_", "env_file": ".env", "extra": "ignore"}

    provider: Literal["qwen", "openai", "siliconflow"] = "siliconflow"
    model: str = "Qwen/Qwen3-8B"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096


class EmbeddingSettings(BaseSettings):
    model_config = {"env_prefix": "EMBEDDING_", "env_file": ".env", "extra": "ignore"}

    model: str = "BAAI/bge-large-zh-v1.5"
    device: str = "cpu"
    dimension: int = 1024


class MilvusSettings(BaseSettings):
    model_config = {"env_prefix": "MILVUS_", "env_file": ".env", "extra": "ignore"}

    host: str = "localhost"
    port: int = 19530
    collection_name: str = "research_docs"
    dimension: int = 1024


class ChromaSettings(BaseSettings):
    model_config = {"env_prefix": "CHROMA_", "env_file": ".env", "extra": "ignore"}

    persist_dir: str = "./data/chroma_db"
    collection_name: str = "research_docs"


class RetrievalSettings(BaseSettings):
    model_config = {"env_prefix": "RETRIEVAL_", "env_file": ".env", "extra": "ignore"}

    top_k: int = 5
    retry_top_k_multiplier: int = 2
    max_retries: int = 3
    critique_threshold: float = 0.6
    rrf_k: int = 60
    vector_backend: Literal["milvus", "chroma"] = "chroma"


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "ignore"}

    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)

    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")


settings = Settings()
