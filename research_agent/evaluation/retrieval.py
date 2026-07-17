"""Deterministic retrieval evaluation metrics and runner."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate retrieval evaluation cases from JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation dataset must contain a non-empty 'cases' list")

    seen_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Each evaluation case must be an object")
        case_id = str(case.get("id", "")).strip()
        query = str(case.get("query", "")).strip()
        expected = case.get("expected_sources")
        match_mode = case.get("match", "any")
        if not case_id or case_id in seen_ids:
            raise ValueError(f"Evaluation case has an invalid or duplicate id: {case_id!r}")
        if not query:
            raise ValueError(f"Evaluation case {case_id!r} has an empty query")
        if not isinstance(expected, list) or not expected or not all(str(item).strip() for item in expected):
            raise ValueError(f"Evaluation case {case_id!r} must define expected_sources")
        if match_mode not in {"any", "all"}:
            raise ValueError(f"Evaluation case {case_id!r} has invalid match mode: {match_mode!r}")
        seen_ids.add(case_id)
    return cases


def _result_source_candidates(result: Any) -> list[str]:
    metadata = getattr(result, "metadata", None)
    if metadata is None and isinstance(result, dict):
        metadata = result.get("metadata", {})
    metadata = metadata or {}
    values = [
        metadata.get("file_name"),
        metadata.get("source"),
        metadata.get("doc_title"),
        metadata.get("source_path"),
    ]
    return [str(value).lower() for value in values if value]


def _source_rank(expected_source: str, results: list[Any]) -> int | None:
    needle = expected_source.strip().lower()
    for rank, result in enumerate(results, start=1):
        if any(needle in candidate for candidate in _result_source_candidates(result)):
            return rank
    return None


def evaluate_case(case: dict[str, Any], results: list[Any], latency_ms: float = 0.0) -> dict[str, Any]:
    """Score one ranked result list against expected source filenames."""
    expected_sources = [str(item) for item in case["expected_sources"]]
    ranks = {source: _source_rank(source, results) for source in expected_sources}
    matched_count = sum(rank is not None for rank in ranks.values())
    match_mode = case.get("match", "any")
    hit_at_k = matched_count == len(expected_sources) if match_mode == "all" else matched_count > 0
    first_rank = min((rank for rank in ranks.values() if rank is not None), default=None)

    return {
        "id": case["id"],
        "query": case["query"],
        "expected_sources": expected_sources,
        "match": match_mode,
        "source_ranks": ranks,
        "hit_at_1": first_rank == 1,
        "hit_at_k": hit_at_k,
        "reciprocal_rank": 1.0 / first_rank if first_rank else 0.0,
        "source_recall": matched_count / len(expected_sources),
        "latency_ms": round(latency_ms, 1),
        "returned_sources": [
            (_result_source_candidates(result) or [""])[0]
            for result in results
        ],
    }


def summarize_results(results: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    """Aggregate hit rate, MRR, source recall, and latency."""
    if not results:
        return {
            "case_count": 0,
            "top_k": top_k,
            "hit_at_1_rate": 0.0,
            "hit_at_k_rate": 0.0,
            "mean_reciprocal_rank": 0.0,
            "mean_source_recall": 0.0,
            "average_latency_ms": 0.0,
        }

    count = len(results)
    return {
        "case_count": count,
        "top_k": top_k,
        "hit_at_1_rate": round(sum(item["hit_at_1"] for item in results) / count, 4),
        "hit_at_k_rate": round(sum(item["hit_at_k"] for item in results) / count, 4),
        "mean_reciprocal_rank": round(sum(item["reciprocal_rank"] for item in results) / count, 4),
        "mean_source_recall": round(sum(item["source_recall"] for item in results) / count, 4),
        "average_latency_ms": round(sum(item["latency_ms"] for item in results) / count, 1),
    }


def run_retrieval_evaluation(
    cases: list[dict[str, Any]],
    search: Callable[[str, int], list[Any]],
    top_k: int = 5,
) -> dict[str, Any]:
    """Run a retrieval function over all cases and return a JSON-ready report."""
    case_results: list[dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        ranked_results = search(str(case["query"]), top_k)
        latency_ms = (time.perf_counter() - started) * 1000
        case_results.append(evaluate_case(case, ranked_results, latency_ms))

    return {
        "summary": summarize_results(case_results, top_k),
        "cases": case_results,
    }
