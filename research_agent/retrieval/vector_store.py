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


class MilvusVectorStore:
    """Milvus / Zilliz Cloud vector store for document retrieval.

    Supports both self-hosted Milvus (host:port) and Zilliz Cloud (uri + token).
    """

    def __init__(self, lazy: bool = False):
        self._client = None
        self._collection_name = settings.milvus.collection_name
        self._dimension = settings.milvus.dimension
        if not lazy:
            self._ensure_collection()

    def _get_client(self):
        if self._client is None:
            from pymilvus import MilvusClient

            milvus_cfg = settings.milvus
            if milvus_cfg.uri:
                self._client = MilvusClient(
                    uri=milvus_cfg.uri,
                    token=milvus_cfg.token,
                )
            else:
                uri = f"http://{milvus_cfg.host}:{milvus_cfg.port}"
                self._client = MilvusClient(uri=uri)

        return self._client

    def _ensure_collection(self) -> None:
        client = self._get_client()
        if not client.has_collection(self._collection_name):
            client.create_collection(
                collection_name=self._collection_name,
                dimension=self._dimension,
                metric_type="COSINE",
            )

    def add_documents(
        self, ids: list[str], texts: list[str], metadatas: list[dict] | None = None
    ) -> None:
        """Add documents to the vector store."""
        from research_agent.retrieval.embedding import get_embedding_service

        emb_service = get_embedding_service()
        embeddings = emb_service.embed(texts).tolist()

        data = [
            {"id": id_, "vector": emb, "text": text, **((metadatas or [{}] * len(texts))[i])}
            for i, (id_, emb, text) in enumerate(zip(ids, embeddings, texts))
        ]

        client = self._get_client()
        client.insert(collection_name=self._collection_name, data=data)

    def search(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        """Semantic vector search via Milvus."""
        from research_agent.retrieval.embedding import get_embedding_service

        top_k = top_k or settings.retrieval.top_k
        emb_service = get_embedding_service()
        query_emb = emb_service.embed_query(query).tolist()

        client = self._get_client()
        results = client.search(
            collection_name=self._collection_name,
            data=[query_emb],
            limit=top_k,
            output_fields=["id", "text", "*"],
        )

        output = []
        for hit_list in results:
            for hit in hit_list:
                entity = hit.get("entity", {})
                chunk_id = entity.get("id", str(hit.get("id", "")))
                content = entity.get("text", "")

                # Milvus returns distance (COSINE: 0=identical, 2=opposite)
                distance = hit.get("distance", 1.0)
                score = max(0.0, 1.0 - distance)

                metadata = {
                    k: v for k, v in entity.items()
                    if k not in ("id", "text", "vector")
                }

                output.append(
                    RetrievalResult(
                        chunk_id=chunk_id,
                        content=content,
                        score=score,
                        metadata=metadata,
                    )
                )

        return output

    @property
    def count(self) -> int:
        client = self._get_client()
        try:
            stats = client.get_collection_stats(self._collection_name)
            return stats.get("row_count", 0)
        except Exception:
            return 0


def create_vector_store() -> VectorStore | MilvusVectorStore:
    """Factory: returns the configured vector store backend."""
    backend = settings.retrieval.vector_backend
    if backend == "milvus":
        return MilvusVectorStore()
    return VectorStore()
