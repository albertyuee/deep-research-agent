"""Local, web and hybrid retrieval node."""

from __future__ import annotations

import asyncio

from config.settings import settings
from research_agent.llm.factory import create_llm_client
from research_agent.retrieval.bm25 import BM25Retriever
from research_agent.retrieval.hybrid import HybridRetriever
from research_agent.retrieval.rewriter import RewriteAction, rewrite_query
from research_agent.retrieval.strategy import select_strategy
from research_agent.reasoning.context import (
    build_contextual_search_query,
    render_step_context,
)
from research_agent.state import ResearchState

from research_agent.nodes.common import (
    _dbg,
    _get_bm25,
    _get_vector_store,
    _research_step_progress,
    _retry_top_k,
    _timed_call,
    emit,
)

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
        query = await _timed_call(
            task_id,
            "reasoning_query",
            lambda: build_contextual_search_query(client, query, available_contexts),
            step=step_idx + 1,
            attempt=retry_count,
        )
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
        strategy = await _timed_call(
            task_id,
            "strategy_selection",
            lambda: select_strategy(client, query),
            step=step_idx + 1,
            attempt=retry_count,
        )

    # On retry, rewrite the query
    if retry_count > 0:
        action_map = {1: RewriteAction.BROADEN, 2: RewriteAction.SWITCH_KEYWORDS, 3: RewriteAction.REPHRASE}
        action = action_map.get(retry_count, RewriteAction.REPHRASE)
        query = await _timed_call(
            task_id,
            "query_rewrite",
            lambda: rewrite_query(client, query, action),
            step=step_idx + 1,
            attempt=retry_count,
        )

    state["retrieval_strategy"] = strategy

    total_steps = state["total_steps"]
    retr_progress = _research_step_progress(step_idx, total_steps, 0.0)

    # Start web search before local retrieval. The local vector/BM25 work is
    # moved to a worker thread below, allowing both sources to overlap.
    web_task: asyncio.Task[list[dict]] | None = None
    if data_source in ("web", "both"):
        emit(task_id, "web_search_start", {
            "step": step_idx + 1,
            "total": total_steps,
            "query": query,
            "progress": _research_step_progress(step_idx, total_steps, 0.45),
        })
        from research_agent.tools.web_search import search_web
        web_task = asyncio.create_task(_timed_call(
            task_id,
            "web_search",
            lambda: search_web(query),
            step=step_idx + 1,
            attempt=retry_count,
            category="web_search",
        ))

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
            top_k = _retry_top_k(retry_count)

            if strategy == "semantic":
                results = await _timed_call(
                    task_id,
                    "local_retrieval",
                    lambda: asyncio.to_thread(
                        hybrid.search_vector_only,
                        query,
                        top_k=top_k,
                        allowed_upload_ids=state.get("allowed_upload_ids"),
                    ),
                    step=step_idx + 1,
                    attempt=retry_count,
                )
            elif strategy == "keyword":
                results = await _timed_call(
                    task_id,
                    "local_retrieval",
                    lambda: asyncio.to_thread(
                        hybrid.search_keyword_only,
                        query,
                        top_k=top_k,
                        allowed_upload_ids=state.get("allowed_upload_ids"),
                    ),
                    step=step_idx + 1,
                    attempt=retry_count,
                )
            else:
                results = await _timed_call(
                    task_id,
                    "local_retrieval",
                    lambda: asyncio.to_thread(
                        hybrid.search,
                        query,
                        top_k=top_k,
                        allowed_upload_ids=state.get("allowed_upload_ids"),
                    ),
                    step=step_idx + 1,
                    attempt=retry_count,
                )

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
                "progress": _research_step_progress(step_idx, total_steps, 0.45),
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
                    "progress": _research_step_progress(step_idx, total_steps, 0.45),
                })
            else:
                # data_source == "local" — no web fallback, re-raise
                raise

    # ── Web Search ──
    web_results = []
    if data_source in ("web", "both"):
        web_results = await web_task if web_task else []

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
            "progress": _research_step_progress(step_idx, total_steps, 0.60),
        })

    # ── Merge: local first, then web ──
    all_results = local_results + web_results
    state["retrieval_results"] = all_results

    combined_progress = _research_step_progress(step_idx, total_steps, 0.65)
    emit(task_id, "retrieval_combined", {
        "step": step_idx + 1,
        "local_count": len(local_results),
        "web_count": len(web_results),
        "total_count": len(all_results),
        "progress": combined_progress,
    })

    return state
