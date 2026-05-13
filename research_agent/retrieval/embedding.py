from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from config.settings import settings


class EmbeddingService:
    """Wrapper around sentence-transformers for embedding generation."""

    def __init__(self, model_name: str | None = None, device: str | None = None):
        model_name = model_name or settings.embedding.model
        device = device or settings.embedding.device
        self.model = SentenceTransformer(model_name, device=device)

    def embed(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        return self.model.encode(texts, normalize_embeddings=True)

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query."""
        return self.model.encode([query], normalize_embeddings=True)[0]

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()


# Singleton
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
