from __future__ import annotations

import numpy as np
from typing import Literal


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


class EmbeddingService:
    """Embedding service supporting both local and API modes."""

    def __init__(
        self,
        mode: Literal["local", "api"] | None = None,
        model_name: str | None = None,
        device: str | None = None,
        api_base_url: str | None = None,
        api_key: str | None = None,
    ):
        settings = _get_settings()
        
        self.mode = mode or settings.embedding.mode
        self.model_name = model_name or settings.embedding.model
        self.device = device or settings.embedding.device
        self.api_base_url = api_base_url or settings.embedding.api_base_url
        self.api_key = api_key or settings.embedding.api_key

        if self.mode == "api" and not self.api_key:
            self.mode = "local"

    def _embed_local(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using local sentence-transformers model."""
        model = _get_local_model()
        return model.encode(texts, normalize_embeddings=True)

    def _embed_api(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using SiliconFlow API."""
        import httpx

        embeddings = []
        batch_size = 32

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

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
            response.raise_for_status()
            result = response.json()
            embeddings.extend([item["embedding"] for item in result["data"]])

        return np.array(embeddings)

    def embed(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        if self.mode == "api":
            return self._embed_api(texts)
        return self._embed_local(texts)

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query."""
        if self.mode == "api":
            result = self._embed_api([query])
            return result[0]
        model = _get_local_model()
        return model.encode([query], normalize_embeddings=True)[0]

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
