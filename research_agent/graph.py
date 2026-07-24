"""LangGraph orchestration facade for Deep Research Agent.

The implementation is split into focused node modules. This module keeps the
public graph API stable for the backend and existing integrations while
retaining the small amount of workflow wiring in one place.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from config.settings import settings
from research_agent.llm.factory import create_llm_client
from research_agent.state import ResearchState

from research_agent.nodes import critique as _critique_nodes
from research_agent.nodes import planning as _planning_nodes
from research_agent.nodes import research as _research_nodes
from research_agent.nodes import retrieval as _retrieval_nodes
from research_agent.nodes.common import (
    _cap_sub_queries,
    _dbg,
    _get_bm25,
    _get_vector_store,
    _research_step_progress,
    _retry_top_k,
    _timed_call,
    emit,
)
from research_agent.nodes.critique import _advance_to_next_step
from research_agent.nodes.planning import _normalize_sub_queries
from research_agent.nodes.synthesis import synthesis_node as _synthesis_node


async def decomposition_node(state: ResearchState) -> ResearchState:
    """Compatibility wrapper for the decomposition node."""
    _planning_nodes.create_llm_client = create_llm_client
    _planning_nodes.emit = emit
    return await _planning_nodes.decomposition_node(state)


async def retrieval_node(state: ResearchState) -> ResearchState:
    """Compatibility wrapper preserving the historical patch seam."""
    _retrieval_nodes.create_llm_client = create_llm_client
    _retrieval_nodes.emit = emit
    return await _retrieval_nodes.retrieval_node(state)


async def critique_node(state: ResearchState) -> ResearchState:
    """Compatibility wrapper for the critique node."""
    _critique_nodes.create_llm_client = create_llm_client
    _critique_nodes.emit = emit
    return await _critique_nodes.critique_node(state)


async def research_node(state: ResearchState) -> ResearchState:
    """Compatibility wrapper preserving scheduler test injection points."""
    _research_nodes._run_research_step = _run_research_step
    _research_nodes.emit = emit
    return await _research_nodes.research_node(state)


def should_retry(state: ResearchState) -> str:
    """Route to synthesis after all steps, otherwise continue research."""
    task_id = state.get("task_id", "")
    step_idx = state.get("current_step", 0)
    total = state.get("total_steps", 1)
    route = "synthesis" if step_idx >= total else "retrieval"
    _dbg(task_id, f"should_retry: step={step_idx}/{total} → {route}")
    return route


# Keep this helper importable for existing tests and integrations that inject a
# fake branch runner into the dependency scheduler.
_run_research_step = _research_nodes._run_research_step
synthesis_node = _synthesis_node


def build_graph() -> StateGraph:
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(ResearchState)
    workflow.add_node("decomposition", decomposition_node)
    workflow.add_node("research", research_node)
    workflow.add_node("synthesis", _synthesis_node)
    workflow.set_entry_point("decomposition")
    workflow.add_edge("decomposition", "research")
    workflow.add_edge("research", "synthesis")
    workflow.add_edge("synthesis", END)
    return workflow.compile()


__all__ = [
    "build_graph",
    "decomposition_node",
    "retrieval_node",
    "critique_node",
    "research_node",
    "synthesis_node",
    "should_retry",
]
