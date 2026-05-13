"""Tests for retrieval modules."""

import pytest
from research_agent.retrieval.bm25 import BM25Retriever


class TestBM25Retriever:
    def test_tokenize_chinese(self):
        tokens = BM25Retriever._tokenize("人工智能在医疗中的应用")
        assert "人工智能" not in tokens  # split per character, not word
        assert "医" in tokens
        assert "疗" in tokens

    def test_tokenize_mixed(self):
        tokens = BM25Retriever._tokenize("IL-6 抑制剂 2023年临床试验")
        assert "il" in tokens  # lowercased
        assert "6" in tokens
        assert "2023" in tokens

    def test_index_and_search(self):
        bm25 = BM25Retriever()
        ids = ["1", "2", "3"]
        texts = [
            "人工智能医疗影像诊断系统",
            "药物研发中的深度学习应用",
            "医疗影像AI系统在CT扫描中的应用",
        ]
        bm25.index_documents(ids, texts)

        assert bm25.is_indexed

        results = bm25.search("医疗影像 CT", top_k=2)
        assert len(results) > 0
        assert results[0].score >= results[-1].score

    def test_search_empty_corpus(self):
        bm25 = BM25Retriever()
        results = bm25.search("anything")
        assert results == []

    def test_is_indexed_before_index(self):
        bm25 = BM25Retriever()
        assert not bm25.is_indexed


class TestHybridRetrieval:
    def test_hybrid_result_dataclass(self):
        from research_agent.retrieval.hybrid import HybridResult
        r = HybridResult(
            chunk_id="test_1",
            content="test content",
            vector_score=0.8,
            bm25_score=0.6,
            combined_score=0.76,
        )
        assert r.combined_score > r.bm25_score
