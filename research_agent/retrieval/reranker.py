from __future__ import annotations

from dataclasses import dataclass

import httpx

from config.settings import settings


@dataclass(frozen=True)
class RerankResult:
    index: int
    relevance_score: float


class SiliconFlowReranker:
    """SiliconFlow rerank client for second-stage retrieval reranking."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        instruction: str | None = None,
        timeout: float | None = None,
    ):
        self.api_key = api_key or settings.rerank.api_key or settings.llm.api_key or settings.embedding.api_key
        self.base_url = (base_url or settings.rerank.base_url).rstrip("/")
        self.model = model or settings.rerank.model
        self.instruction = instruction or settings.rerank.instruction
        self.timeout = timeout or settings.rerank.timeout

    @property
    def is_enabled(self) -> bool:
        return settings.rerank.enabled and bool(self.api_key)

    def rerank(self, query: str, documents: list[str], top_n: int | None = None) -> list[RerankResult]:
        if not documents:
            return []

        limit = min(top_n or settings.rerank.top_n or len(documents), len(documents))
        payload: dict = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": limit,
            "return_documents": False,
        }
        if self.model.startswith("Qwen/Qwen3-Reranker") and self.instruction:
            payload["instruction"] = self.instruction

        response = httpx.post(
            f"{self.base_url}/rerank",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("results", []):
            try:
                results.append(
                    RerankResult(
                        index=int(item["index"]),
                        relevance_score=float(item.get("relevance_score", 0.0)),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return results


def create_reranker() -> SiliconFlowReranker | None:
    if not settings.rerank.enabled:
        return None
    reranker = SiliconFlowReranker()
    return reranker if reranker.is_enabled else None
