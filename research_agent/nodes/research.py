"""Dependency-layer scheduler for bounded parallel research."""

from __future__ import annotations

import asyncio
import copy

from config.settings import settings
from research_agent.state import ResearchState

from research_agent.nodes.common import _dbg, _timed_call, emit
from research_agent.nodes.critique import critique_node
from research_agent.nodes.retrieval import retrieval_node

def _isolated_step_state(state: ResearchState, step_idx: int) -> ResearchState:
    """Create mutable per-step state so concurrent branches never share writes."""
    isolated: ResearchState = dict(state)
    isolated["current_step"] = step_idx
    isolated["retry_count"] = 0
    isolated["retry_history"] = []
    isolated["low_confidence_steps"] = []
    isolated["completed_steps"] = list(state.get("completed_steps", []))
    isolated["step_contexts"] = copy.deepcopy(state.get("step_contexts", {}))
    isolated["step_results"] = copy.deepcopy(state.get("step_results", {}))
    isolated["step_critiques"] = copy.deepcopy(state.get("step_critiques", {}))
    isolated["reasoning_paths"] = []
    isolated["all_retrieval_results"] = []
    isolated["all_critique_results"] = []
    return isolated


async def _run_research_step(
    state: ResearchState,
    step_idx: int,
    semaphore: asyncio.Semaphore,
) -> tuple[int, ResearchState]:
    """Run one step, including all configured retries, in an isolated branch."""
    async with semaphore:
        step_state = _isolated_step_state(state, step_idx)
        step_number = step_idx + 1
        task_id = state.get("task_id", "")

        async def execute() -> ResearchState:
            while step_number not in step_state.get("completed_steps", []):
                # critique_node changes current_step only after this target is
                # complete; retries continue to use the original step index.
                step_state["current_step"] = step_idx
                await retrieval_node(step_state)
                await critique_node(step_state)
            return step_state

        completed_state = await _timed_call(
            task_id,
            "research_step",
            execute,
            step=step_number,
        )
        return step_idx, completed_state


def _merge_step_state(state: ResearchState, step_idx: int, branch: ResearchState) -> None:
    """Merge only the target step's outputs back into the shared state."""
    step_number = step_idx + 1
    step_key = str(step_number)

    if step_key in branch.get("step_results", {}):
        state.setdefault("step_results", {})[step_key] = branch["step_results"][step_key]
    if step_key in branch.get("step_critiques", {}):
        state.setdefault("step_critiques", {})[step_key] = branch["step_critiques"][step_key]
    if step_key in branch.get("step_contexts", {}):
        state.setdefault("step_contexts", {})[step_key] = branch["step_contexts"][step_key]

    if step_number in branch.get("low_confidence_steps", []):
        low_confidence = state.setdefault("low_confidence_steps", [])
        if step_number not in low_confidence:
            low_confidence.append(step_number)

    state.setdefault("retry_history", []).extend(branch.get("retry_history", []))
    state.setdefault("reasoning_paths", []).extend(branch.get("reasoning_paths", []))
    completed = state.setdefault("completed_steps", [])
    if step_number not in completed:
        completed.append(step_number)
    state["hop_count"] = max(state.get("hop_count", 0), branch.get("hop_count", 0))


async def research_node(state: ResearchState) -> ResearchState:
    """Execute ready dependency layers with bounded step concurrency."""
    task_id = state.get("task_id", "")
    sub_queries = state.get("sub_queries", [])
    max_hops = state.get("max_hops", settings.reasoning.max_hops)
    concurrency = max(1, settings.retrieval.max_concurrency)
    semaphore = asyncio.Semaphore(concurrency)

    pending = {
        index
        for index, step in enumerate(sub_queries)
        if int(step.get("hop", 1)) <= max_hops
    }
    skipped = set(range(len(sub_queries))) - pending
    for index in sorted(skipped):
        state.setdefault("low_confidence_steps", []).append(index + 1)

    while pending:
        completed = set(state.get("completed_steps", []))
        ready = [
            index
            for index in sorted(pending)
            if {
                int(dep)
                for dep in sub_queries[index].get("depends_on", [])
                if str(dep).isdigit()
            }.issubset(completed)
        ]
        if not ready:
            # A malformed/cyclic plan should still finish deterministically.
            ready = [min(pending)]
            _dbg(task_id, f"dependency cycle fallback: step={ready[0] + 1}")

        emit(task_id, "research_layer_start", {
            "steps": [index + 1 for index in ready],
            "concurrency": concurrency,
        })
        branches = await _timed_call(
            task_id,
            "research_layer",
            lambda: asyncio.gather(*(
                _run_research_step(state, index, semaphore)
                for index in ready
            )),
        )
        for step_idx, branch in sorted(branches, key=lambda item: item[0]):
            _merge_step_state(state, step_idx, branch)
            pending.discard(step_idx)

    state["completed_steps"] = sorted(set(state.get("completed_steps", [])))
    state["low_confidence_steps"] = sorted(set(state.get("low_confidence_steps", [])))
    state["all_retrieval_results"] = [
        state.get("step_results", {}).get(str(index + 1), [])
        for index in range(len(sub_queries))
    ]
    state["all_critique_results"] = [
        state.get("step_critiques", {}).get(str(index + 1), {})
        for index in range(len(sub_queries))
    ]
    state["current_step"] = len(sub_queries)
    return state
