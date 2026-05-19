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

from research_agent.state import ResearchState
from research_agent.streaming import event_bus
from research_agent.llm.factory import create_llm_client
from research_agent.planner.decomposer import decompose_query
from research_agent.planner.research_plan import ResearchPlan
from research_agent.retrieval.strategy import select_strategy
from research_agent.retrieval.hybrid import HybridRetriever
from research_agent.retrieval.vector_store import VectorStore
from research_agent.retrieval.bm25 import BM25Retriever
from research_agent.retrieval.rewriter import rewrite_query, RewriteAction
from research_agent.critique.scorer import critique_retrieval
from research_agent.critique.retry_controller import RetryState
from research_agent.synthesis.aggregator import aggregate_results
from research_agent.synthesis.report_generator import generate_report_streaming
from research_agent.synthesis.citation import build_citation_map, build_references_section, format_citation, Citation
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

    _dbg(task_id, "decomposition_node ENTER")
    emit(task_id, "research_plan_start", {"query": query, "progress": 0.05})

    _dbg(task_id, "creating LLM client...")
    client = create_llm_client()
    _dbg(task_id, f"calling decompose_query (model={client.model}, web={enable_web_search})...")
    t0 = _time.time()
    try:
        sub_queries = await decompose_query(client, query, enable_web_search)
        _dbg(task_id, f"decompose_query OK after {_time.time()-t0:.1f}s, {len(sub_queries)} sub-queries")
    except Exception as e:
        _dbg(task_id, f"decompose_query FAILED after {_time.time()-t0:.1f}s: {e}")
        raise

    plan = ResearchPlan.from_decomposition(query, sub_queries)

    total_sub = len(sub_queries)
    for sq in sub_queries:
        p = 0.05 + (sq["index"] / total_sub) * 0.05
        emit(task_id, "research_plan_chunk", {
            "index": sq["index"],
            "question": sq["question"],
            "strategy": sq["strategy"],
            "rationale": sq.get("rationale", ""),
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

    # Determine strategy — on retry, may switch strategy
    client = create_llm_client()
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
                "metadata": {**r.metadata, "strategy": strategy, "source": "local"},
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
                "content": r["content"][:200],
                "score": r["score"],
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
        "retry_suggestion": critique.retry_suggestion,
        "progress": crit_res_progress,
    })

    # ── Post-critique state management (moved from should_retry) ──
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", settings.retrieval.max_retries)

    if critique.passed:
        _save_step_results(state)
        state["current_step"] = step_idx + 1
        state["retry_count"] = 0
    elif retry_count < max_retries - 1:
        state["retry_count"] = retry_count + 1
        state["retry_history"].append({
            "step": step_idx,
            "attempt": retry_count + 1,
            "score": critique.composite_score,
        })
    else:
        state["low_confidence_steps"].append(step_idx + 1)
        _save_step_results(state)
        state["current_step"] = step_idx + 1
        state["retry_count"] = 0

    return state


# ──────────────────── Node: Synthesis ────────────────────


async def synthesis_node(state: ResearchState) -> ResearchState:
    """Aggregate all findings and generate the final report."""
    task_id = state.get("task_id", "")

    emit(task_id, "synthesis_start", {"total_steps": state["total_steps"], "progress": 0.60})

    sub_queries = state["sub_queries"]
    all_results = state["all_retrieval_results"]
    all_critiques = state["all_critique_results"]

    # Ensure we have results for all steps (pad if needed)
    while len(all_results) < len(sub_queries):
        all_results.append([])

    # Aggregate
    sq_texts = [sq["question"] for sq in sub_queries]
    findings = aggregate_results(sq_texts, all_results, all_critiques)
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

    state["all_retrieval_results"] = all_results
    state["all_critique_results"] = all_critiques


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


_vector_store: VectorStore | None = None
_bm25: BM25Retriever | None = None


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def _get_bm25() -> BM25Retriever:
    global _bm25
    if _bm25 is None:
        _bm25 = BM25Retriever()
    return _bm25


def emit(task_id: str, event_type: str, data: dict | None = None) -> None:
    """Emit an SSE event via the global event bus."""
    if task_id:
        event_bus.emit(task_id, event_type, data or {})
