"""Tests for dependency-aware multi-hop retrieval."""

from typing import NamedTuple

import pytest

from research_agent import graph as graph_module
from research_agent.graph import _advance_to_next_step, retrieval_node
from research_agent.reasoning.context import (
    build_contextual_search_query,
    extract_step_context,
    render_step_context,
)


class FakeResult(NamedTuple):
    chunk_id: str
    content: str
    score: float
    metadata: dict


class CapturingVectorStore:
    def __init__(self):
        self.query = ""

    def search(self, query, top_k=None):
        self.query = query
        return [FakeResult("chunk-2", "下一跳证据", 0.9, {})]


class EmptyBM25:
    is_indexed = False


class StructuredClient:
    async def chat_structured(self, messages, schema, **kwargs):
        return {
            "summary": "Transformer 用于医疗影像。",
            "entities": ["Transformer", "医疗影像"],
            "facts": ["Transformer 可用于影像分析"],
            "open_questions": ["它在药物研发中如何使用？"],
        }


class QueryClient:
    async def chat_structured(self, messages, schema, **kwargs):
        return {"query": "Transformer 在药物研发中的应用"}


@pytest.mark.asyncio
async def test_context_extraction_keeps_source_ids():
    context = await extract_step_context(
        StructuredClient(),
        "原始问题",
        "第一跳",
        [{"chunk_id": "chunk-1", "content": "Transformer 用于医疗影像。"}],
    )

    assert context["entities"] == ["Transformer", "医疗影像"]
    assert context["source_ids"] == ["chunk-1"]
    assert "已确认事实" in render_step_context([context])


@pytest.mark.asyncio
async def test_contextual_search_query_is_short_and_independent():
    query = await build_contextual_search_query(
        QueryClient(),
        "这种方法如何应用？",
        [{"summary": "很长的摘要" * 500, "entities": ["Transformer"]}],
    )

    assert query == "Transformer 在药物研发中的应用"
    assert len(query) <= 400


@pytest.mark.asyncio
async def test_dependent_retrieval_uses_previous_step_context(monkeypatch):
    vector_store = CapturingVectorStore()
    monkeypatch.setattr(graph_module, "create_llm_client", lambda: object())
    state = {
        "query": "比较两类应用",
        "current_step": 1,
        "total_steps": 2,
        "retry_count": 0,
        "sub_queries": [
            {"index": 1, "question": "识别方法", "strategy": "semantic"},
            {
                "index": 2,
                "question": "这种方法在药物研发中如何使用？",
                "strategy": "semantic",
                "depends_on": [1],
                "hop": 2,
                "data_source": "local",
            },
        ],
        "step_contexts": {
            "1": {
                "summary": "第一跳识别出 Transformer。",
                "entities": ["Transformer"],
                "facts": ["Transformer 用于医疗影像"],
            }
        },
        "_vector_store": vector_store,
        "_bm25": EmptyBM25(),
    }

    await retrieval_node(state)

    assert "Transformer" in vector_store.query
    assert len(vector_store.query) <= 400


def test_scheduler_respects_dependencies_and_hop_budget():
    state = {
        "sub_queries": [
            {"index": 1, "hop": 1, "depends_on": []},
            {"index": 2, "hop": 2, "depends_on": [1]},
            {"index": 3, "hop": 4, "depends_on": [2]},
        ],
        "completed_steps": [1],
        "max_hops": 2,
        "low_confidence_steps": [],
    }

    _advance_to_next_step(state)
    assert state["current_step"] == 1

    state["completed_steps"] = [1, 2]
    _advance_to_next_step(state)
    assert state["current_step"] == 3
    assert state["low_confidence_steps"] == [3]
