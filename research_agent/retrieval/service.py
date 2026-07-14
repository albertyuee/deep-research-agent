"""Shared retrieval service for vector, BM25, and hybrid search lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any

from research_agent.retrieval.bm25 import BM25Retriever
from research_agent.retrieval.hybrid import HybridRetriever
from research_agent.retrieval.vector_store import create_vector_store


class RetrievalService:
    """Own the process-wide retrieval backends and keep BM25 synchronized."""

    def __init__(self, vector_store_factory: Callable[[], Any] | None = None):
        self._vector_store_factory = vector_store_factory or create_vector_store
        self._vector_store: Any | None = None
        self._bm25 = BM25Retriever()
        self._bm25_initialized = False
        self._lock = RLock()

    def get_vector_store(self):
        with self._lock:
            if self._vector_store is None:
                self._vector_store = self._vector_store_factory()
            return self._vector_store

    def get_bm25(self) -> BM25Retriever:
        with self._lock:
            if not self._bm25_initialized:
                self.rebuild_bm25()
            return self._bm25

    def get_hybrid(self) -> HybridRetriever:
        return HybridRetriever(self.get_vector_store(), self.get_bm25())

    def rebuild_bm25(self, vector_store=None) -> int:
        """Rebuild BM25 from the persistent vector store and return chunk count."""
        with self._lock:
            store = vector_store or self.get_vector_store()
            ids, documents, metadatas = store.get_all_documents()
            self._bm25.index_documents(ids, documents, metadatas)
            self._bm25_initialized = True
            return len(ids)

    def reset(self) -> None:
        """Drop cached backends after a configuration change."""
        with self._lock:
            self._vector_store = None
            self._bm25 = BM25Retriever()
            self._bm25_initialized = False


retrieval_service = RetrievalService()
