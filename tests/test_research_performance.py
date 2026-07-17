"""Performance-oriented orchestration tests without external API calls."""

import asyncio
import threading
from typing import NamedTuple

import pytest

from research_agent import graph as graph_module
from research_agent.graph import retrieval_node
from research_agent.observability.timing import collect_timings, record_timing


class FakeResult(NamedTuple):
    chunk_id: str
    content: str
    score: float
    metadata: dict


class CoordinatedVectorStore:
    def __init__(self, local_started: threading.Event, web_started: threading.Event):
        self.local_started = local_started
        self.web_started = web_started

    def search(self, query, top_k=None):
        self.local_started.set()
        assert self.web_started.wait(1), "web search did not overlap local retrieval"
        return [FakeResult("local-1", "local evidence", 0.9, {})]


class EmptyBM25:
    is_indexed = False


@pytest.mark.asyncio
async def test_local_and_web_retrieval_overlap(monkeypatch):
    local_started = threading.Event()
    web_started = threading.Event()

    async def fake_web_search(query):
        web_started.set()
        assert await asyncio.to_thread(local_started.wait, 1)
        return [{
            "chunk_id": "web-1",
            "content": "web evidence",
            "score": 0.8,
            "metadata": {"title": "Web", "url": "https://example.test"},
        }]

    monkeypatch.setattr(graph_module, "create_llm_client", lambda: object())
    monkeypatch.setattr("research_agent.tools.web_search.search_web", fake_web_search)

    state = {
        "query": "compare",
        "current_step": 0,
        "total_steps": 1,
        "retry_count": 0,
        "sub_queries": [{
            "index": 1,
            "question": "compare",
            "strategy": "semantic",
            "data_source": "both",
        }],
        "_vector_store": CoordinatedVectorStore(local_started, web_started),
        "_bm25": EmptyBM25(),
    }

    result = await retrieval_node(state)

    assert {item["chunk_id"] for item in result["retrieval_results"]} == {"local-1", "web-1"}


def test_timing_metric_inherits_operation_context():
    with collect_timings("task-1", "critique", step=2, attempt=1) as metrics:
        record_timing("llm", 123.456, details={"model": "test"})

    assert len(metrics) == 1
    assert metrics[0].as_dict() == {
        "category": "llm",
        "operation": "critique",
        "duration_ms": 123.5,
        "step": 2,
        "attempt": 1,
        "details": {"model": "test"},
    }
