"""Agent state definition for the Deep Research Agent."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict


ResearchMode = Literal["auto", "parallel", "multihop"]


class RetrievalStep(TypedDict, total=False):
    sub_query: str
    strategy: str
    results: list[dict]
    critique_score: float
    critique_passed: bool
    retry_count: int


class ResearchState(TypedDict, total=False):
    # Input
    query: str
    task_id: str
    enable_web_search: bool
    research_mode: ResearchMode
    reasoning_enabled: bool

    # Decomposition
    sub_queries: list[dict]
    research_plan: dict
    total_steps: int
    current_step: int

    # Retrieval (per step)
    retrieval_results: list[dict]
    retrieval_strategy: str

    # Critique
    critique_result: dict
    critique_passed: bool
    retry_count: int

    # Retry
    retry_history: list[dict]
    low_confidence_steps: list[int]
    max_retries: int

    # Multi-hop reasoning
    completed_steps: list[int]
    step_contexts: dict[str, dict]
    step_results: dict[str, list[dict]]
    step_critiques: dict[str, dict]
    reasoning_paths: list[list[int]]
    hop_count: int
    max_hops: int

    # Synthesis
    aggregated_findings: list[dict]
    all_retrieval_results: list[list[dict]]
    all_critique_results: list[dict]
    final_report: str
    sources: list[dict]

    # Control
    next_node: str
    error: str
