from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from research_agent.retrieval.vector_store import VectorStore, RetrievalResult
from research_agent.retrieval.bm25 import BM25Retriever, BM25Result
from research_agent.retrieval.reranker import RerankResult, create_reranker
from config.settings import settings


class RerankerProtocol(Protocol):
    @property
    def is_enabled(self) -> bool: ...

    def rerank(self, query: str, documents: list[str], top_n: int | None = None) -> list[RerankResult]: ...


@dataclass
class HybridResult:
    chunk_id: str
    content: str
    vector_score: float = 0.0
    bm25_score: float = 0.0
    combined_score: float = 0.0
    rerank_score: float | None = None
    metadata: dict = field(default_factory=dict)


class HybridRetriever:
    """Combined vector + BM25 retrieval with optional reranking."""

    def __init__(
        self,
        vector_store: VectorStore,
        bm25: BM25Retriever,
        reranker: RerankerProtocol | None = None,
    ):
        self.vector_store = vector_store
        self.bm25 = bm25
        self.rrf_k = settings.retrieval.rrf_k
        self.reranker = reranker if reranker is not None else create_reranker()

    def search(
        self, query: str, top_k: int | None = None, vector_weight: float = 0.5
    ) -> list[HybridResult]:
        """Execute hybrid search with RRF fusion and optional reranking."""
        top_k = top_k or settings.retrieval.top_k
        candidate_top_k = self._candidate_top_k(top_k)

        # Get results from both retrievers
        vector_results = self.vector_store.search(query, top_k=candidate_top_k)
        bm25_results = self.bm25.search(query, top_k=candidate_top_k) if self.bm25.is_indexed else []

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

        # Sort by combined score, optionally rerank, then return top_k
        sorted_results = sorted(fused.values(), key=lambda x: x.combined_score, reverse=True)
        return self._rerank_results(query, sorted_results, top_k)

    def search_vector_only(self, query: str, top_k: int | None = None) -> list[HybridResult]:
        top_k = top_k or settings.retrieval.top_k
        results = self.vector_store.search(query, top_k=self._candidate_top_k(top_k))
        hybrid_results = [
            HybridResult(
                chunk_id=r.chunk_id,
                content=r.content,
                vector_score=r.score,
                combined_score=r.score,
                metadata=r.metadata,
            )
            for r in results
        ]
        return self._rerank_results(query, hybrid_results, top_k)

    def search_keyword_only(self, query: str, top_k: int | None = None) -> list[HybridResult]:
        if not self.bm25.is_indexed:
            return []
        top_k = top_k or settings.retrieval.top_k
        results = self.bm25.search(query, top_k=self._candidate_top_k(top_k))
        hybrid_results = [
            HybridResult(
                chunk_id=r.chunk_id,
                content=r.content,
                bm25_score=r.score,
                combined_score=r.score,
                metadata=r.metadata,
            )
            for r in results
        ]
        return self._rerank_results(query, hybrid_results, top_k)

    def _candidate_top_k(self, top_k: int) -> int:
        multiplier = settings.rerank.candidate_multiplier if self._rerank_enabled else 2
        return max(top_k, top_k * max(multiplier, 1))

    @property
    def _rerank_enabled(self) -> bool:
        return bool(self.reranker and self.reranker.is_enabled)

    def _rerank_results(self, query: str, results: list[HybridResult], top_k: int) -> list[HybridResult]:
        if not self._rerank_enabled or len(results) <= 1:
            return results[:top_k]

        try:
            reranked = self.reranker.rerank(
                query,
                [r.content for r in results],
                top_n=min(settings.rerank.top_n or top_k, top_k, len(results)),
            )
        except Exception:
            return results[:top_k]

        ordered: list[HybridResult] = []
        seen: set[int] = set()
        for item in reranked:
            if item.index < 0 or item.index >= len(results) or item.index in seen:
                continue
            seen.add(item.index)
            result = results[item.index]
            result.metadata = {
                **result.metadata,
                "pre_rerank_score": result.combined_score,
                "rerank_model": settings.rerank.model,
            }
            result.rerank_score = item.relevance_score
            result.combined_score = item.relevance_score
            ordered.append(result)

        if len(ordered) < top_k:
            ordered.extend(r for i, r in enumerate(results) if i not in seen)

        return ordered[:top_k]
