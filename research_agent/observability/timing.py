"""Structured timing collection for deep-research operations.

Low-level clients record metrics into a context-local sink. The graph flushes
that sink on the event-loop thread so SSE delivery remains thread-safe even
when blocking retrieval work runs through ``asyncio.to_thread``.
"""

from __future__ import annotations

import json
import sys
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class TimingContext:
    task_id: str
    operation: str
    step: int | None = None
    attempt: int | None = None


@dataclass
class TimingMetric:
    category: str
    operation: str
    duration_ms: float
    step: int | None = None
    attempt: int | None = None
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "operation": self.operation,
            "duration_ms": round(self.duration_ms, 1),
            "step": self.step,
            "attempt": self.attempt,
            "details": self.details,
        }


_context: ContextVar[TimingContext | None] = ContextVar("research_timing_context", default=None)
_sink: ContextVar[list[TimingMetric] | None] = ContextVar("research_timing_sink", default=None)
_task_metrics: dict[str, list[dict]] = {}
_metrics_lock = threading.Lock()


@contextmanager
def collect_timings(
    task_id: str,
    operation: str,
    *,
    step: int | None = None,
    attempt: int | None = None,
) -> Iterator[list[TimingMetric]]:
    """Collect nested timing calls under one graph operation."""
    metrics: list[TimingMetric] = []
    context_token = _context.set(TimingContext(task_id, operation, step, attempt))
    sink_token = _sink.set(metrics)
    try:
        yield metrics
    finally:
        _sink.reset(sink_token)
        _context.reset(context_token)


def record_timing(
    category: str,
    duration_ms: float,
    *,
    operation: str | None = None,
    details: dict | None = None,
) -> TimingMetric:
    """Record one metric in the active operation and write a structured log."""
    context = _context.get()
    metric = TimingMetric(
        category=category,
        operation=operation or (context.operation if context else "unknown"),
        duration_ms=max(0.0, duration_ms),
        step=context.step if context else None,
        attempt=context.attempt if context else None,
        details=details or {},
    )
    sink = _sink.get()
    if sink is not None:
        sink.append(metric)

    task_label = context.task_id if context else "unscoped"
    print(
        f"[TIMING {task_label}] {json.dumps(metric.as_dict(), ensure_ascii=False)}",
        flush=True,
        file=sys.stderr,
    )
    return metric


def emit_timing_events(task_id: str, metrics: list[TimingMetric]) -> None:
    """Persist metrics and emit them from the event-loop thread."""
    if not task_id or not metrics:
        return
    payloads = [metric.as_dict() for metric in metrics]
    with _metrics_lock:
        _task_metrics.setdefault(task_id, []).extend(payloads)

    from research_agent.streaming import event_bus

    for payload in payloads:
        event_bus.emit(task_id, "timing", payload)


def drain_task_timings(task_id: str) -> list[dict]:
    """Remove and return all metrics collected for a terminal task."""
    with _metrics_lock:
        return _task_metrics.pop(task_id, [])
