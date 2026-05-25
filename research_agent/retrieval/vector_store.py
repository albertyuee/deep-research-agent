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

    def delete_by_upload_id(self, upload_id: str) -> int:
        """Delete all chunks belonging to an uploaded document."""
        matched = self.collection.get(
            where={"upload_id": upload_id},
            include=["metadatas"],
        )
        ids = matched.get("ids", []) if matched else []
        if not ids:
            return 0

        self.collection.delete(ids=ids)
        return len(ids)

    def get_all_documents(self) -> tuple[list[str], list[str], list[dict]]:
        """Return all indexed chunks for rebuilding keyword indexes."""
        data = self.collection.get(include=["documents", "metadatas"])
        if not data or not data.get("ids"):
            return [], [], []
        return (
            data["ids"],
            data.get("documents") or [],
            data.get("metadatas") or [],
        )

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
            from research_agent.retrieval.embedding import get_embedding_service

            # Auto-detect actual embedding dimension
            emb_service = get_embedding_service()
            dim = emb_service.dimension
            self._dimension = dim

            client.create_collection(
                collection_name=self._collection_name,
                dimension=dim,
                metric_type="COSINE",
                auto_id=True,
            )

    def add_documents(
        self, ids: list[str], texts: list[str], metadatas: list[dict] | None = None
    ) -> None:
        """Add documents to the vector store.

        Milvus auto-generates int64 primary keys. We store the original chunk_id
        as a separate 'chunk_id' field for retrieval.
        """
        from research_agent.retrieval.embedding import get_embedding_service

        emb_service = get_embedding_service()
        embeddings = emb_service.embed(texts).tolist()
        meta_list = metadatas or [{}] * len(texts)

        data = [
            {
                "chunk_id": id_,
                "vector": emb,
                "text": text,
                **meta,
            }
            for id_, emb, text, meta in zip(ids, embeddings, texts, meta_list)
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
            output_fields=["chunk_id", "text", "*"],
        )

        output = []
        for hit_list in results:
            for hit in hit_list:
                entity = hit.get("entity", {})
                chunk_id = entity.get("chunk_id", "")
                content = entity.get("text", "")

                # Milvus returns distance (COSINE: 0=identical, 2=opposite)
                distance = hit.get("distance", 1.0)
                score = max(0.0, 1.0 - distance)

                metadata = {
                    k: v for k, v in entity.items()
                    if k not in ("chunk_id", "text", "vector")
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

    @staticmethod
    def _string_literal(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def delete_by_upload_id(self, upload_id: str) -> int:
        """Delete all chunks belonging to an uploaded document."""
        client = self._get_client()
        expr = f"upload_id == {self._string_literal(upload_id)}"
        matched = client.query(
            collection_name=self._collection_name,
            filter=expr,
            output_fields=["chunk_id"],
            limit=16384,
        )
        if not matched:
            return 0

        result = client.delete(collection_name=self._collection_name, filter=expr)
        if isinstance(result, dict):
            return int(result.get("delete_count") or result.get("delete_cnt") or len(matched))
        return int(getattr(result, "delete_count", len(matched)))

    def get_all_documents(self) -> tuple[list[str], list[str], list[dict]]:
        """Return all indexed chunks for rebuilding keyword indexes."""
        client = self._get_client()
        try:
            rows = client.query(
                collection_name=self._collection_name,
                filter="",
                output_fields=["chunk_id", "text", "*"],
                limit=16384,
            )
        except Exception:
            rows = client.query(
                collection_name=self._collection_name,
                filter="chunk_id != ''",
                output_fields=["chunk_id", "text", "*"],
                limit=16384,
            )
        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []
        for row in rows:
            chunk_id = row.get("chunk_id", "")
            text = row.get("text", "")
            if not chunk_id or text is None:
                continue
            ids.append(chunk_id)
            texts.append(text)
            metadatas.append({
                k: v for k, v in row.items()
                if k not in ("chunk_id", "text", "vector")
            })
        return ids, texts, metadatas

    @property
    def count(self) -> int:
        client = self._get_client()
        try:
            stats = client.get_collection_stats(self._collection_name)
            return stats.get("row_count", 0)
        except Exception:
            # Fallback: try describe_collection
            try:
                info = client.describe_collection(self._collection_name)
                return info.get("num_entities", 0)
            except Exception:
                return 0


def create_vector_store() -> VectorStore | MilvusVectorStore:
    """Factory: returns the configured vector store backend."""
    backend = settings.retrieval.vector_backend
    if backend == "milvus":
        return MilvusVectorStore()
    return VectorStore()
