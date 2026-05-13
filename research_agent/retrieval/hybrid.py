from __future__ import annotations

from dataclasses import dataclass, field

from research_agent.retrieval.vector_store import VectorStore, RetrievalResult
from research_agent.retrieval.bm25 import BM25Retriever, BM25Result
from config.settings import settings


@dataclass
class HybridResult:
    chunk_id: str
    content: str
    vector_score: float = 0.0
    bm25_score: float = 0.0
    combined_score: float = 0.0
    metadata: dict = field(default_factory=dict)


class HybridRetriever:
    """Combined vector + BM25 retrieval with RRF fusion."""

    def __init__(self, vector_store: VectorStore, bm25: BM25Retriever):
        self.vector_store = vector_store
        self.bm25 = bm25
        self.rrf_k = settings.retrieval.rrf_k

    def search(
        self, query: str, top_k: int | None = None, vector_weight: float = 0.5
    ) -> list[HybridResult]:
        """Execute hybrid search with RRF fusion."""
        top_k = top_k or settings.retrieval.top_k

        # Get results from both retrievers
        vector_results = self.vector_store.search(query, top_k=top_k * 2)
        bm25_results = self.bm25.search(query, top_k=top_k * 2) if self.bm25.is_indexed else []

        # RRF fusion
        fused: dict[str, HybridResult] = {}

        # Vector scores
        for rank, vr in enumerate(vector_results):
            rrf_score = 1.0 / (self.rrf_k + rank + 1)
            fused[vr.chunk_id] = HybridResult(
                chunk_id=vr.chunk_id,
                content=vr.content,
                vector_score=vr.score,
                combined_score=rrf_score * vector_weight,
                metadata=vr.metadata,
            )

        # BM25 scores
        for rank, br in enumerate(bm25_results):
            rrf_score = 1.0 / (self.rrf_k + rank + 1)
            if br.chunk_id in fused:
                fused[br.chunk_id].bm25_score = br.score
                fused[br.chunk_id].combined_score += rrf_score * (1 - vector_weight)
            else:
                fused[br.chunk_id] = HybridResult(
                    chunk_id=br.chunk_id,
                    content=br.content,
                    bm25_score=br.score,
                    combined_score=rrf_score * (1 - vector_weight),
                    metadata=br.metadata,
                )

        # Sort by combined score and return top_k
        sorted_results = sorted(fused.values(), key=lambda x: x.combined_score, reverse=True)
        return sorted_results[:top_k]

    def search_vector_only(self, query: str, top_k: int | None = None) -> list[HybridResult]:
        results = self.vector_store.search(query, top_k=top_k)
        return [
            HybridResult(
                chunk_id=r.chunk_id,
                content=r.content,
                vector_score=r.score,
                combined_score=r.score,
                metadata=r.metadata,
            )
            for r in results
        ]

    def search_keyword_only(self, query: str, top_k: int | None = None) -> list[HybridResult]:
        if not self.bm25.is_indexed:
            return []
        results = self.bm25.search(query, top_k=top_k or settings.retrieval.top_k)
        return [
            HybridResult(
                chunk_id=r.chunk_id,
                content=r.content,
                bm25_score=r.score,
                combined_score=r.score,
                metadata=r.metadata,
            )
            for r in results
        ]
