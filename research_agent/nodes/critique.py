"""Retrieval quality evaluation, retry and step advancement node."""

from __future__ import annotations

from config.settings import settings
from research_agent.critique.scorer import critique_retrieval
from research_agent.llm.factory import create_llm_client
from research_agent.reasoning.context import extract_step_context
from research_agent.state import ResearchState

from research_agent.nodes.common import (
    _dbg,
    _research_step_progress,
    _timed_call,
    emit,
)

async def critique_node(state: ResearchState) -> ResearchState:
    """Evaluate retrieval quality, decide pass/fail, and handle step advancement.

    This node also handles post-critique state updates that were previously
    in the conditional edge function (should_retry), since LangGraph conditional
    edge functions must be pure (no state mutation).
    """
    task_id = state.get("task_id", "")
    step_idx = state["current_step"]
    total = state.get("total_steps", 1)

    crit_progress = _research_step_progress(step_idx, total, 0.75)
    emit(task_id, "critique_start", {"step": step_idx + 1, "progress": crit_progress})

    client = create_llm_client()
    sub_q = state["sub_queries"][step_idx]
    results = state.get("retrieval_results", [])

    result_texts = [r["content"] for r in results]
    critique = await _timed_call(
        task_id,
        "critique",
        lambda: critique_retrieval(client, sub_q["question"], result_texts),
        step=step_idx + 1,
        attempt=state.get("retry_count", 0),
    )

    state["critique_result"] = {
        "composite_score": critique.composite_score,
        "relevance_score": critique.relevance_score,
        "completeness_score": critique.completeness_score,
        "passed": critique.passed,
        "reasoning": critique.reasoning,
        "retry_suggestion": critique.retry_suggestion,
    }
    state["critique_passed"] = critique.passed

    crit_res_progress = _research_step_progress(step_idx, total, 1.0)
    emit(task_id, "critique_result", {
        "step": step_idx + 1,
        "composite_score": critique.composite_score,
        "relevance": critique.relevance_score,
        "completeness": critique.completeness_score,
        "passed": critique.passed,
        "reasoning": critique.reasoning,
        "retry_suggestion": critique.retry_suggestion,
        "progress": crit_res_progress,
    })

    # ── Post-critique state management (moved from should_retry) ──
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", settings.retrieval.max_retries)

    should_finalize = critique.passed or retry_count >= max_retries
    if critique.passed:
        _save_step_results(state)
        state["retry_count"] = 0
    elif retry_count < max_retries:
        state["retry_count"] = retry_count + 1
        state["retry_history"].append({
            "step": step_idx,
            "attempt": retry_count + 1,
            "score": critique.composite_score,
        })
        emit(task_id, "retry_triggered", {
            "step": step_idx + 1,
            "count": retry_count + 1,
            "suggestion": critique.retry_suggestion,
            "progress": crit_res_progress,
        })
    else:
        state["low_confidence_steps"].append(step_idx + 1)
        _save_step_results(state)
        state["retry_count"] = 0

    if should_finalize:
        step_number = step_idx + 1
        completed_steps = state.setdefault("completed_steps", [])
        if step_number not in completed_steps:
            completed_steps.append(step_number)

        dependent_steps = [
            item for item in state["sub_queries"]
            if step_number in item.get("depends_on", [])
        ]
        if dependent_steps and state.get("reasoning_enabled", settings.reasoning.enabled):
            try:
                context = await _timed_call(
                    task_id,
                    "context_extraction",
                    lambda: extract_step_context(
                        client,
                        state["query"],
                        sub_q["question"],
                        results,
                    ),
                    step=step_number,
                    attempt=retry_count,
                )
            except Exception as exc:
                _dbg(task_id, f"Step context extraction failed: {exc}")
                context = {
                    "summary": "\n".join(
                        (item.get("content") or "")[:500] for item in results[:3]
                    ),
                    "entities": [],
                    "facts": [],
                    "open_questions": [],
                    "source_ids": [
                        str(item.get("chunk_id", "unknown")) for item in results[:5]
                    ],
                }
            context["quality_score"] = critique.composite_score
            context["low_confidence"] = not critique.passed
            state.setdefault("step_contexts", {})[str(step_number)] = context
            emit(task_id, "reasoning_context", {
                "step": step_number,
                "hop": sub_q.get("hop", 1),
                "depends_on": sub_q.get("depends_on", []),
                "summary": context.get("summary", ""),
                "entity_count": len(context.get("entities", [])),
                "fact_count": len(context.get("facts", [])),
                "low_confidence": context.get("low_confidence", False),
                "progress": crit_res_progress,
            })

        state["hop_count"] = max(
            state.get("hop_count", 0), int(sub_q.get("hop", 1))
        )
        state.setdefault("reasoning_paths", []).append(
            [*sub_q.get("depends_on", []), step_number]
        )
        _advance_to_next_step(state)

    return state

def _save_step_results(state: ResearchState) -> None:
    """Save current step results to the accumulated lists."""
    all_results = state.get("all_retrieval_results", [])
    all_critiques = state.get("all_critique_results", [])
    step_idx = len(all_results)  # append in order

    all_results.append(state.get("retrieval_results", []))
    all_critiques.append(state.get("critique_result", {}))

    step_number = state.get("current_step", 0) + 1
    state.setdefault("step_results", {})[str(step_number)] = state.get(
        "retrieval_results", []
    )
    state.setdefault("step_critiques", {})[str(step_number)] = state.get(
        "critique_result", {}
    )

    state["all_retrieval_results"] = all_results
    state["all_critique_results"] = all_critiques


def _advance_to_next_step(state: ResearchState) -> None:
    """Select the first pending step whose dependencies are complete."""
    completed = set(state.get("completed_steps", []))
    total = len(state.get("sub_queries", []))
    max_hops = state.get("max_hops", settings.reasoning.max_hops)

    for index, step in enumerate(state.get("sub_queries", [])):
        step_number = index + 1
        if step_number in completed:
            continue
        if int(step.get("hop", 1)) > max_hops:
            continue
        dependencies = {
            int(dep) for dep in step.get("depends_on", []) if str(dep).isdigit()
        }
        if dependencies.issubset(completed):
            state["current_step"] = index
            return

    # Preserve a safe linear fallback if an otherwise eligible plan step has
    # malformed dependencies; steps beyond the configured hop budget are not run.
    for index, step in enumerate(state.get("sub_queries", [])):
        if (
            index + 1 not in completed
            and int(step.get("hop", 1)) <= max_hops
        ):
            state["current_step"] = index
            return

    skipped_steps = [
        index + 1
        for index, step in enumerate(state.get("sub_queries", []))
        if index + 1 not in completed and int(step.get("hop", 1)) > max_hops
    ]
    for step_number in skipped_steps:
        if step_number not in state.setdefault("low_confidence_steps", []):
            state["low_confidence_steps"].append(step_number)
    state["current_step"] = total
