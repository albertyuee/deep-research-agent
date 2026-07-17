"""Tests for deterministic retrieval evaluation metrics and dataset schema."""

from pathlib import Path
from types import SimpleNamespace

from research_agent.evaluation.retrieval import (
    evaluate_case,
    load_cases,
    summarize_results,
)


DATASET = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "retrieval_cases.json"


def _result(source: str):
    return SimpleNamespace(metadata={"file_name": source})


def test_public_retrieval_dataset_is_valid_and_private_data_free():
    cases = load_cases(DATASET)

    assert len(cases) >= 7
    assert len({case["id"] for case in cases}) == len(cases)
    assert all("刘悦" not in case["query"] for case in cases)


def test_evaluate_case_records_rank_and_reciprocal_rank():
    case = {
        "id": "langgraph",
        "query": "stateful agent",
        "expected_sources": ["langchain_langgraph.md"],
        "match": "any",
    }

    result = evaluate_case(case, [_result("other.md"), _result("langchain_langgraph.md")])

    assert result["source_ranks"]["langchain_langgraph.md"] == 2
    assert result["hit_at_1"] is False
    assert result["hit_at_k"] is True
    assert result["reciprocal_rank"] == 0.5


def test_all_match_mode_requires_every_expected_source():
    case = {
        "id": "comparison",
        "query": "compare",
        "expected_sources": ["haystack.md", "llamaindex.md"],
        "match": "all",
    }

    result = evaluate_case(case, [_result("haystack.md")])

    assert result["hit_at_k"] is False
    assert result["source_recall"] == 0.5


def test_summary_aggregates_core_metrics():
    summary = summarize_results(
        [
            {"hit_at_1": True, "hit_at_k": True, "reciprocal_rank": 1.0, "source_recall": 1.0, "latency_ms": 10.0},
            {"hit_at_1": False, "hit_at_k": False, "reciprocal_rank": 0.0, "source_recall": 0.0, "latency_ms": 30.0},
        ],
        top_k=5,
    )

    assert summary["hit_at_1_rate"] == 0.5
    assert summary["hit_at_k_rate"] == 0.5
    assert summary["mean_reciprocal_rank"] == 0.5
    assert summary["average_latency_ms"] == 20.0
