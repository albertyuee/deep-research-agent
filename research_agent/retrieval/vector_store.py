from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import numpy as np
import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings


class RetrievalResult(NamedTuple):
    chunk_id: str
    content: str
    score: float
    metadata: dict


class VectorStore:
    """Chroma-based vector store for document retrieval."""

    def __init__(self):
        cfg = settings.chroma
        persist_dir = str(cfg.resolved_persist_dir)
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=cfg.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self, ids: list[str], texts: list[str], metadatas: list[dict] | None = None
    ) -> None:
        """Add documents to the vector store."""
        from research_agent.retrieval.embedding import get_embedding_service

        emb_service = get_embedding_service()
        embeddings = emb_service.embed(texts).tolist()

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas or [{}] * len(texts),
        )

    def search(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        """Semantic vector search."""
        from research_agent.retrieval.embedding import get_embedding_service

        top_k = top_k or settings.retrieval.top_k
        emb_service = get_embedding_service()
        query_emb = emb_service.embed_query(query).tolist()

        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1.0 - distance  # cosine distance → similarity
                output.append(
                    RetrievalResult(
                        chunk_id=chunk_id,
                        content=results["documents"][0][i] if results["documents"] else "",
                        score=max(0.0, score),
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    )
                )

        return output

    @property
    def count(self) -> int:
        return self.collection.count()
