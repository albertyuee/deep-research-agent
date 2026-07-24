"""Shared helpers used by the research graph nodes.

Keeping timing, progress and event-bus helpers here prevents each node from
reimplementing cross-cutting behavior while keeping the graph facade small.
"""

from __future__ import annotations

import sys
import time as _time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from config.settings import settings
from research_agent.observability.timing import (
    collect_timings,
    emit_timing_events,
    record_timing,
)
from research_agent.retrieval.bm25 import BM25Retriever
from research_agent.retrieval.service import retrieval_service
from research_agent.streaming import event_bus


T = TypeVar("T")


def _dbg(task_id: str, msg: str) -> None:
    """Write an agent diagnostic line to the Uvicorn stderr log."""
    print(f"[AGENT-DBG {task_id}] {msg}", flush=True, file=sys.stderr)


def _research_step_progress(step_idx: int, total_steps: int, fraction: float) -> float:
    """Map a step-local fraction onto the monotonic 10%-60% range."""
    total = max(total_steps, 1)
    bounded_step = min(max(step_idx, 0), total - 1)
    bounded_fraction = min(max(fraction, 0.0), 1.0)
    return 0.10 + ((bounded_step + bounded_fraction) / total) * 0.50


def _cap_sub_queries(sub_queries: list[dict]) -> list[dict]:
    """Apply the configured planner output limit defensively."""
    return sub_queries[: max(1, settings.reasoning.max_sub_queries)]


def _retry_top_k(retry_count: int) -> int:
    """Expand retrieval breadth on retry without exceeding the hard cap."""
    expanded = settings.retrieval.top_k * (
        settings.retrieval.retry_top_k_multiplier ** max(0, retry_count)
    )
    return min(expanded, settings.retrieval.max_top_k)


async def _timed_call(
    task_id: str,
    operation: str,
    call: Callable[[], Awaitable[T]],
    *,
    step: int | None = None,
    attempt: int | None = None,
    category: str = "stage",
) -> T:
    """Run an async operation and emit its low-level and stage timings."""
    with collect_timings(
        task_id,
        operation,
        step=step,
        attempt=attempt,
    ) as metrics:
        started = _time.perf_counter()
        try:
            return await call()
        finally:
            record_timing(category, (_time.perf_counter() - started) * 1000)
            emit_timing_events(task_id, metrics)


def _get_vector_store():
    return retrieval_service.get_vector_store()


def _get_bm25() -> BM25Retriever:
    return retrieval_service.get_bm25()


def emit(task_id: str, event_type: str, data: dict | None = None) -> None:
    """Emit an SSE event via the global event bus."""
    if task_id:
        event_bus.emit(task_id, event_type, data or {})
