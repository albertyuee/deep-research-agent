"""Problem decomposition and research-plan normalization node."""

from __future__ import annotations

import time as _time

from config.settings import settings
from research_agent.llm.factory import create_llm_client
from research_agent.planner.decomposer import decompose_query
from research_agent.planner.research_plan import ResearchPlan
from research_agent.state import ResearchMode, ResearchState

from research_agent.nodes.common import (
    _cap_sub_queries,
    _dbg,
    _timed_call,
    emit,
)

async def decomposition_node(state: ResearchState) -> ResearchState:
    """Decompose the user query into sub-questions and create a research plan."""
    task_id = state.get("task_id", "")
    query = state["query"]
    enable_web_search = state.get("enable_web_search", False)
    research_mode: ResearchMode = state.get("research_mode", "auto")
    max_hops = state.get("max_hops", settings.reasoning.max_hops)
    reasoning_enabled = (
        research_mode == "multihop"
        or (research_mode == "auto" and settings.reasoning.enabled)
    )

    _dbg(task_id, "decomposition_node ENTER")
    emit(task_id, "research_plan_start", {
        "query": query,
        "research_mode": research_mode,
        "max_hops": max_hops,
        "progress": 0.05,
    })

    _dbg(task_id, "creating LLM client...")
    client = create_llm_client()
    _dbg(task_id, f"calling decompose_query (model={client.model}, web={enable_web_search})...")
    t0 = _time.time()
    try:
        sub_queries = await _timed_call(
            task_id,
            "decomposition",
            lambda: decompose_query(
                client,
                query,
                enable_web_search,
                research_mode,
                max_hops,
            ),
        )
        _dbg(task_id, f"decompose_query OK after {_time.time()-t0:.1f}s, {len(sub_queries)} sub-queries")
    except Exception as e:
        _dbg(task_id, f"decompose_query FAILED after {_time.time()-t0:.1f}s: {e}")
        raise

    # Enforce the server-side limit even if the model ignores the JSON schema.
    sub_queries = _cap_sub_queries(sub_queries)

    # A provider failure or malformed structured response should still produce
    # a useful single-step research task instead of crashing in critique_node.
    if not sub_queries:
        sub_queries = [{
            "index": 1,
            "question": query,
            "strategy": "hybrid",
            "data_source": "local",
            "rationale": "规划结果为空，回退为对原始问题进行混合检索。",
        }]

    plan = ResearchPlan.from_decomposition(query, sub_queries)
    sub_queries = _normalize_sub_queries(
        sub_queries,
        plan,
        research_mode,
        reasoning_enabled,
        max_hops,
    )
    plan = ResearchPlan.from_decomposition(query, sub_queries)

    total_sub = len(sub_queries)
    for sq in sub_queries:
        p = 0.05 + (sq["index"] / total_sub) * 0.05
        emit(task_id, "research_plan_chunk", {
            "index": sq["index"],
            "question": sq["question"],
            "strategy": sq["strategy"],
            "data_source": sq.get("data_source", "local"),
            "rationale": sq.get("rationale", ""),
            "hop": sq.get("hop", 1),
            "depends_on": sq.get("depends_on", []),
            "progress": p,
        })

    state["sub_queries"] = sub_queries
    state["research_plan"] = plan.model_dump()
    state["total_steps"] = plan.step_count
    state["current_step"] = 0
    state["all_retrieval_results"] = []
    state["all_critique_results"] = []
    state["retry_count"] = 0
    state["retry_history"] = []
    state["low_confidence_steps"] = []
    state["max_retries"] = settings.retrieval.max_retries
    state["research_mode"] = research_mode
    state["reasoning_enabled"] = reasoning_enabled
    state["completed_steps"] = []
    state["step_contexts"] = {}
    state["step_results"] = {}
    state["step_critiques"] = {}
    state["reasoning_paths"] = []
    state["hop_count"] = 0
    state["max_hops"] = max_hops

    _dbg(task_id, "decomposition_node EXIT")
    return state

def _normalize_sub_queries(
    sub_queries: list[dict],
    plan: ResearchPlan,
    research_mode: ResearchMode,
    reasoning_enabled: bool,
    max_hops: int,
) -> list[dict]:
    """Apply task-level research mode without relying on global settings."""
    normalized_sub_queries: list[dict] = []

    for position, (raw, step) in enumerate(zip(sub_queries, plan.steps)):
        step_number = position + 1
        dependencies = [
            int(dep)
            for dep in step.depends_on
            if 1 <= int(dep) < step_number
        ] if reasoning_enabled else []

        if research_mode == "multihop" and position > 0 and not dependencies:
            dependencies = [position]

        hop = 1
        if reasoning_enabled:
            parent_hops = [
                int(normalized_sub_queries[dep - 1].get("hop", 1))
                for dep in dependencies
                if dep <= len(normalized_sub_queries)
            ]
            inferred_hop = max(parent_hops, default=0) + 1 if dependencies else 1
            hop = min(max(step.hop, inferred_hop), max_hops)

        normalized = dict(raw)
        normalized.update({
            "index": step_number,
            "hop": hop,
            "depends_on": dependencies,
            "input_slots": step.input_slots if dependencies else [],
            "terminal": step.terminal,
        })
        normalized_sub_queries.append(normalized)

    return normalized_sub_queries
