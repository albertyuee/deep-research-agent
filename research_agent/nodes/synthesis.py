"""Finding aggregation and streaming report synthesis node."""

from __future__ import annotations

import time as _time

from research_agent.llm.factory import create_llm_client
from research_agent.observability.timing import (
    collect_timings,
    emit_timing_events,
    record_timing,
)
from research_agent.state import ResearchState
from research_agent.synthesis.aggregator import aggregate_results
from research_agent.synthesis.citation import build_citation_map, build_references_section
from research_agent.synthesis.report_generator import generate_report_streaming

from research_agent.nodes.common import emit

async def synthesis_node(state: ResearchState) -> ResearchState:
    """Aggregate all findings and generate the final report."""
    task_id = state.get("task_id", "")

    emit(task_id, "synthesis_start", {"total_steps": state["total_steps"], "progress": 0.60})

    sub_queries = state["sub_queries"]
    step_results = state.get("step_results", {})
    step_critiques = state.get("step_critiques", {})
    all_results = [
        step_results.get(str(index + 1), [])
        for index in range(len(sub_queries))
    ]
    all_critiques = [
        step_critiques.get(str(index + 1), {})
        for index in range(len(sub_queries))
    ]

    # Ensure we have results for all steps (pad if needed)
    while len(all_results) < len(sub_queries):
        all_results.append([])

    # Aggregate
    sq_texts = [sq["question"] for sq in sub_queries]
    findings = aggregate_results(
        sq_texts,
        all_results,
        all_critiques,
        state.get("step_contexts", {}),
    )
    state["aggregated_findings"] = [f.__dict__ for f in findings]

    # Build citation map from all sources
    all_sources = []
    for result_list in all_results:
        for r in result_list:
            if isinstance(r, dict):
                all_sources.append(r)

    citation_map = build_citation_map(all_sources)

    # Generate report with streaming
    client = create_llm_client()
    report_parts = []
    chunk_idx = 0
    with collect_timings(task_id, "synthesis") as metrics:
        started = _time.perf_counter()
        try:
            async for chunk in generate_report_streaming(client, state["query"], findings, citation_map):
                report_parts.append(chunk)
                chunk_idx += 1
                synth_progress = 0.60 + min(chunk_idx * 0.005, 0.30)
                emit(task_id, "synthesis_chunk", {"text": chunk, "progress": synth_progress})
        finally:
            record_timing("stage", (_time.perf_counter() - started) * 1000)
            emit_timing_events(task_id, metrics)

    report = "".join(report_parts)

    # Append references
    refs = build_references_section(citation_map)
    if refs:
        report += f"\n\n{refs}"

    state["final_report"] = report
    state["sources"] = all_sources

    return state
