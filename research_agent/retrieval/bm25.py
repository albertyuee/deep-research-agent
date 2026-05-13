from __future__ import annotations

import re
from typing import NamedTuple

import numpy as np
from rank_bm25 import BM25Okapi


class BM25Result(NamedTuple):
    chunk_id: str
    content: str
    score: float
    metadata: dict


class BM25Retriever:
    """BM25 keyword-based retrieval."""

    def __init__(self):
        self._documents: list[dict] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple Chinese/English tokenizer."""
        # Split on Chinese characters and keep them as individual tokens
        tokens = []
        # Match Chinese chars, English words, and numbers
        for match in re.finditer(r"[\u4e00-\u9fff]|[a-zA-Z]+|\d+", text.lower()):
            tokens.append(match.group())
        return tokens

    def index_documents(
        self, ids: list[str], texts: list[str], metadatas: list[dict] | None = None
    ) -> None:
        """Index documents for BM25 search."""
        metadatas = metadatas or [{}] * len(texts)
        self._documents = [
            {"id": id_, "content": text, "metadata": meta}
            for id_, text, meta in zip(ids, texts, metadatas)
        ]
        self._tokenized_corpus = [self._tokenize(text) for text in texts]
        self._bm25 = BM25Okapi(self._tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> list[BM25Result]:
        """Search using BM25."""
        if self._bm25 is None:
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        max_score = scores.max() if scores.size > 0 else 1.0
        for idx in top_indices:
            if scores[idx] > 0:
                normalized_score = float(scores[idx] / max_score) if max_score > 0 else 0.0
                doc = self._documents[idx]
                results.append(
                    BM25Result(
                        chunk_id=doc["id"],
                        content=doc["content"],
                        score=normalized_score,
                        metadata=doc["metadata"],
                    )
                )

        return results

    @property
    def is_indexed(self) -> bool:
        return self._bm25 is not None
