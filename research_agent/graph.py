"""LangGraph agent orchestration for Deep Research Agent.

Agent flow:
    START → decomposition → retrieval → critique → should_retry?
                                                     ├─ pass + more steps → retrieval
                                                     ├─ pass + done → synthesis
                                                     ├─ fail + can retry → retrieval
                                                     └─ fail + exhausted → advance step → ...

This implements an Agentic RAG pattern where the agent autonomously
decides whether to retry retrieval or proceed to synthesis.
"""

from __future__ import annotations

import sys
import time as _time

from langgraph.graph import StateGraph, END

from research_agent.state import ResearchMode, ResearchState
from research_agent.streaming import event_bus
from research_agent.llm.factory import create_llm_client
from research_agent.planner.decomposer import decompose_query
from research_agent.planner.research_plan import ResearchPlan
from research_agent.retrieval.strategy import select_strategy
from research_agent.retrieval.hybrid import HybridRetriever
from research_agent.retrieval.bm25 import BM25Retriever
from research_agent.retrieval.service import retrieval_service
from research_agent.retrieval.rewriter import rewrite_query, RewriteAction
from research_agent.critique.scorer import critique_retrieval
from research_agent.critique.retry_controller import RetryState
from research_agent.reasoning.context import (
    build_contextual_search_query,
    extract_step_context,
    render_step_context,
)
from research_agent.synthesis.aggregator import aggregate_results
from research_agent.synthesis.report_generator import generate_report_streaming
from research_agent.synthesis.citation import build_citation_map, build_references_section
from config.settings import settings

# Debug helper — prints to stderr (captured by uvicorn log)
def _dbg(task_id: str, msg: str) -> None:
    print(f"[AGENT-DBG {task_id}] {msg}", flush=True, file=sys.stderr)


# ──────────────────── Node: Decomposition ────────────────────


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
        sub_queries = await decompose_query(
            client,
            query,
            enable_web_search,
            research_mode,
            max_hops,
        )
        _dbg(task_id, f"decompose_query OK after {_time.time()-t0:.1f}s, {len(sub_queries)} sub-queries")
    except Exception as e:
        _dbg(task_id, f"decompose_query FAILED after {_time.time()-t0:.1f}s: {e}")
        raise

    # A provider failure or malformed structured response should still produce
    # a useful single-step research task instead of crashing in critique_node.
    if not sub_queries:
        sub_queries = [{
            "index": 1,
            "question": query,
            "strategy": "hybrid",
            "data_source": "local",
            "rationale": "Fallback to the original query.",
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


# ──────────────────── Node: Retrieval ────────────────────


async def retrieval_node(state: ResearchState) -> ResearchState:
    """Execute retrieval for the current sub-query.

    Dispatches to local retrieval (Chroma/BM25) and/or web search (MCP)
    based on the data_source field in the sub-query.
    """
    task_id = state.get("task_id", "")
    step_idx = state["current_step"]
    sub_queries = state["sub_queries"]
    retry_count = state.get("retry_count", 0)

    if step_idx >= len(sub_queries):
        return state

    sub_q = sub_queries[step_idx]
    query = sub_q["question"]
    data_source = sub_q.get("data_source", "local")
    client = create_llm_client()

    dependency_contexts = [
        state.get("step_contexts", {}).get(str(dep), {})
        for dep in sub_q.get("depends_on", [])
    ]
    available_contexts = [context for context in dependency_contexts if context]
    if available_contexts and state.get("reasoning_enabled", settings.reasoning.enabled):
        rendered_context = render_step_context(available_contexts)
        query = await build_contextual_search_query(client, query, available_contexts)
        emit(task_id, "reasoning_query", {
            "step": step_idx + 1,
            "hop": sub_q.get("hop", 1),
            "context_chars": len(rendered_context),
            "query": query,
            "query_chars": len(query),
        })

    # Determine strategy — on retry, may switch strategy
    if retry_count == 0:
        strategy = sub_q.get("strategy", "hybrid")
    elif retry_count == 2:  # 2nd retry: switch strategy
        original = sub_q.get("strategy", "hybrid")
        strategy = "keyword" if original == "semantic" else "semantic"
    else:
        # On retry, re-evaluate strategy
        strategy = await select_strategy(client, query)

    # On retry, rewrite the query
    if retry_count > 0:
        action_map = {1: RewriteAction.BROADEN, 2: RewriteAction.SWITCH_KEYWORDS, 3: RewriteAction.REPHRASE}
        action = action_map.get(retry_count, RewriteAction.REPHRASE)
        query = await rewrite_query(client, query, action)

    state["retrieval_strategy"] = strategy

    total_steps = state["total_steps"]
    retr_progress = 0.10 + (step_idx / max(total_steps, 1)) * 0.30

    # ── Local Retrieval ──
    local_results = []
    local_failed = False
    if data_source in ("local", "both"):
        emit(task_id, "retrieval_start", {
            "step": step_idx + 1,
            "total": total_steps,
            "query": query,
            "strategy": strategy,
            "data_source": "local",
            "retry_count": retry_count,
            "progress": retr_progress,
        })

        try:
            vector_store = state.get("_vector_store") or _get_vector_store()
            bm25 = state.get("_bm25") or _get_bm25()

            if not bm25.is_indexed:
                strategy = "semantic"  # fallback if BM25 not indexed

            hybrid = HybridRetriever(vector_store, bm25)
            top_k = settings.retrieval.top_k * (2 ** retry_count)  # expand k on retry

            if strategy == "semantic":
                results = hybrid.search_vector_only(query, top_k=top_k)
            elif strategy == "keyword":
                results = hybrid.search_keyword_only(query, top_k=top_k)
            else:
                results = hybrid.search(query, top_k=top_k)

            local_results = [
                {
                    "chunk_id": r.chunk_id,
                    "content": r.content,
                    "score": r.combined_score,
                    "vector_score": r.vector_score,
                    "bm25_score": r.bm25_score,
                    "rerank_score": r.rerank_score,
                    "metadata": {**r.metadata, "strategy": strategy, "source_type": "local"},
                }
                for r in results
            ]

            emit(task_id, "retrieval_result", {
                "step": step_idx + 1,
                "result_count": len(local_results),
                "top_score": local_results[0]["score"] if local_results else 0,
                "top_preview": local_results[0]["content"][:200] if local_results else "",
                "data_source": "local",
                "progress": retr_progress + 0.10,
            })

        except Exception as e:
            _dbg(task_id, f"Local retrieval failed: {e}")
            local_failed = True
            if data_source == "both":
                # Web search is available — continue with web results only
                emit(task_id, "retrieval_result", {
                    "step": step_idx + 1,
                    "result_count": 0,
                    "top_score": 0,
                    "top_preview": "",
                    "data_source": "local",
                    "error": str(e),
                    "progress": retr_progress + 0.10,
                })
            else:
                # data_source == "local" — no web fallback, re-raise
                raise

    # ── Web Search ──
    web_results = []
    if data_source in ("web", "both"):
        emit(task_id, "web_search_start", {
            "step": step_idx + 1,
            "total": total_steps,
            "query": query,
            "progress": retr_progress + 0.10,
        })

        from research_agent.tools.web_search import search_web
        web_results = await search_web(query)

        # Build structured result list for frontend rendering
        web_result_items = [
            {
                "title": r["metadata"].get("title", ""),
                "url": r["metadata"].get("url", ""),
                "content": (r.get("content") or "")[:200],
                "score": r.get("score") or 0.0,
            }
            for r in web_results
        ]

        emit(task_id, "web_search_result", {
            "step": step_idx + 1,
            "result_count": len(web_results),
            "results": web_result_items,
            "progress": retr_progress + 0.15,
        })

    # ── Merge: local first, then web ──
    all_results = local_results + web_results
    state["retrieval_results"] = all_results

    combined_progress = 0.10 + ((step_idx + 1) / max(total_steps, 1)) * 0.30
    emit(task_id, "retrieval_combined", {
        "step": step_idx + 1,
        "local_count": len(local_results),
        "web_count": len(web_results),
        "total_count": len(all_results),
        "progress": combined_progress,
    })

    return state


# ──────────────────── Node: Critique ────────────────────


async def critique_node(state: ResearchState) -> ResearchState:
    """Evaluate retrieval quality, decide pass/fail, and handle step advancement.

    This node also handles post-critique state updates that were previously
    in the conditional edge function (should_retry), since LangGraph conditional
    edge functions must be pure (no state mutation).
    """
    task_id = state.get("task_id", "")
    step_idx = state["current_step"]
    total = state.get("total_steps", 1)

    crit_progress = 0.40 + ((step_idx + 1) / max(total, 1)) * 0.05
    emit(task_id, "critique_start", {"step": step_idx + 1, "progress": crit_progress})

    client = create_llm_client()
    sub_q = state["sub_queries"][step_idx]
    results = state.get("retrieval_results", [])

    result_texts = [r["content"] for r in results]
    critique = await critique_retrieval(client, sub_q["question"], result_texts)

    state["critique_result"] = {
        "composite_score": critique.composite_score,
        "relevance_score": critique.relevance_score,
        "completeness_score": critique.completeness_score,
        "passed": critique.passed,
        "reasoning": critique.reasoning,
        "retry_suggestion": critique.retry_suggestion,
    }
    state["critique_passed"] = critique.passed

    crit_res_progress = 0.40 + ((step_idx + 1) / max(total, 1)) * 0.15
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
                context = await extract_step_context(
                    client,
                    state["query"],
                    sub_q["question"],
                    results,
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


# ──────────────────── Node: Synthesis ────────────────────


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
    async for chunk in generate_report_streaming(client, state["query"], findings, citation_map):
        report_parts.append(chunk)
        chunk_idx += 1
        synth_progress = 0.60 + min(chunk_idx * 0.005, 0.30)
        emit(task_id, "synthesis_chunk", {"text": chunk, "progress": synth_progress})

    report = "".join(report_parts)

    # Append references
    refs = build_references_section(citation_map)
    if refs:
        report += f"\n\n{refs}"

    state["final_report"] = report
    state["sources"] = all_sources

    emit(task_id, "done", {"report_length": len(report), "progress": 1.0})

    return state


# ──────────────────── Conditional Edge ────────────────────


def should_retry(state: ResearchState) -> str:
    """Pure routing function — reads state, returns next node.
    All state mutations have been moved to critique_node.

    Returns:
        "retrieval" — go to retrieval node (next step or retry)
        "synthesis" — all steps done, proceed to synthesis
    """
    task_id = state.get("task_id", "")
    step_idx = state.get("current_step", 0)
    total = state.get("total_steps", 1)
    route = "synthesis" if step_idx >= total else "retrieval"
    _dbg(task_id, f"should_retry: step={step_idx}/{total} → {route}")
    return route


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


# ──────────────────── Graph Construction ────────────────────


def build_graph() -> StateGraph:
    """Build the LangGraph StateGraph for the Deep Research Agent."""
    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("decomposition", decomposition_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("synthesis", synthesis_node)

    # Set entry point
    workflow.set_entry_point("decomposition")

    # Edges
    workflow.add_edge("decomposition", "retrieval")
    workflow.add_edge("retrieval", "critique")

    # Conditional edge from critique
    workflow.add_conditional_edges(
        "critique",
        should_retry,
        {
            "retrieval": "retrieval",
            "synthesis": "synthesis",
        },
    )

    workflow.add_edge("synthesis", END)

    return workflow.compile()


# ──────────────────── Helpers ────────────────────


def _get_vector_store():
    return retrieval_service.get_vector_store()


def _get_bm25() -> BM25Retriever:
    return retrieval_service.get_bm25()


def emit(task_id: str, event_type: str, data: dict | None = None) -> None:
    """Emit an SSE event via the global event bus."""
    if task_id:
        event_bus.emit(task_id, event_type, data or {})
