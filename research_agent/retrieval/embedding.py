from __future__ import annotations

import numpy as np
import time
from langsmith import traceable
from typing import Literal

from research_agent.observability.timing import record_timing


def _get_settings():
    """Lazy import settings to avoid import-time issues."""
    from config.settings import settings
    return settings


def _get_local_model():
    """Lazy import and cache local model."""
    from sentence_transformers import SentenceTransformer
    settings = _get_settings()
    return SentenceTransformer(
        settings.embedding.model,
        device=settings.embedding.device
    )


def _summarize_embedding_inputs(inputs: dict) -> dict:
    texts = inputs.get("texts") or []
    query = inputs.get("query")
    return {
        "text_count": len(texts),
        "query": query,
        "max_text_chars": max((len(text) for text in texts), default=0),
    }


def _summarize_embedding_output(output) -> dict:
    shape = getattr(output, "shape", None)
    return {"shape": list(shape) if shape is not None else None}


class EmbeddingService:
    """Embedding service supporting both local and API modes."""

    def __init__(
        self,
        mode: Literal["local", "api"] | None = None,
        model_name: str | None = None,
        device: str | None = None,
        api_base_url: str | None = None,
        api_key: str | None = None,
        query_max_chars: int | None = None,
    ):
        settings = _get_settings()
        
        self.mode = mode or settings.embedding.mode
        self.model_name = model_name or settings.embedding.model
        self.device = device or settings.embedding.device
        self.api_base_url = api_base_url or settings.embedding.api_base_url
        self.api_key = api_key or settings.embedding.api_key
        self.query_max_chars = (
            query_max_chars
            if query_max_chars is not None
            else settings.embedding.query_max_chars
        )

        if self.mode == "api" and not self.api_key:
            self.mode = "local"

    def _embed_local(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using local sentence-transformers model."""
        started = time.perf_counter()
        try:
            model = _get_local_model()
            return model.encode(texts, normalize_embeddings=True)
        finally:
            record_timing(
                "embedding",
                (time.perf_counter() - started) * 1000,
                details={"model": self.model_name, "text_count": len(texts), "mode": "local"},
            )

    def _embed_api(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using SiliconFlow API."""
        import httpx

        embeddings = []
        batch_size = 8

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            max_chars = max(len(t) for t in batch)
            print(f"[EMBED] batch {i//batch_size + 1}: {len(batch)} texts, max_chars={max_chars}", flush=True)

            started = time.perf_counter()
            response = None
            try:
                response = httpx.post(
                    f"{self.api_base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "input": batch,
                    },
                    timeout=60.0,
                )
            finally:
                record_timing(
                    "embedding",
                    (time.perf_counter() - started) * 1000,
                    details={
                        "model": self.model_name,
                        "text_count": len(batch),
                        "status_code": response.status_code if response is not None else None,
                    },
                )
            if not response.is_success:
                detail = response.text[:500]
                print(
                    f"[EMBED] ERROR {response.status_code}: model={self.model_name}, "
                    f"max_chars={max_chars}, response={detail}",
                    flush=True,
                )
                response.raise_for_status()
            result = response.json()
            embeddings.extend([item["embedding"] for item in result["data"]])

        return np.array(embeddings)

    @traceable(
        name="embed_documents",
        run_type="embedding",
        process_inputs=_summarize_embedding_inputs,
        process_outputs=_summarize_embedding_output,
    )
    def embed(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        if self.mode == "api":
            return self._embed_api(texts)
        return self._embed_local(texts)

    @traceable(
        name="embed_query",
        run_type="embedding",
        process_inputs=_summarize_embedding_inputs,
        process_outputs=_summarize_embedding_output,
    )
    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query."""
        prepared_query = self._prepare_query(query)
        if self.mode == "api":
            result = self._embed_api([prepared_query])
            return result[0]
        started = time.perf_counter()
        try:
            model = _get_local_model()
            return model.encode([prepared_query], normalize_embeddings=True)[0]
        finally:
            record_timing(
                "embedding",
                (time.perf_counter() - started) * 1000,
                details={"model": self.model_name, "text_count": 1, "mode": "local"},
            )

    def _prepare_query(self, query: str) -> str:
        """Bound query size before it reaches a model-specific token limit."""
        normalized = " ".join(query.split())
        if len(normalized) > self.query_max_chars:
            print(
                f"[EMBED] query truncated: {len(normalized)} -> {self.query_max_chars} chars",
                flush=True,
            )
        return normalized[: self.query_max_chars]

    @property
    def dimension(self) -> int:
        if self.mode == "api":
            model_dimensions = {
                "BAAI/bge-large-zh-v1.5": 1024,
                "BAAI/bge-small-zh-v1.5": 512,
                "Pro/BAAI/bge-large-zh-v1.5": 1024,
            }
            return model_dimensions.get(self.model_name, 1024)
        settings = _get_settings()
        return settings.embedding.dimension


# Singleton
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def reset_embedding_service():
    """Reset the singleton (useful for testing or config changes)."""
    global _embedding_service
    _embedding_service = None
