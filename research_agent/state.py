"""Agent state definition for the Deep Research Agent."""

from __future__ import annotations

from typing import Annotated, TypedDict


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

    # Synthesis
    aggregated_findings: list[dict]
    all_retrieval_results: list[list[dict]]
    all_critique_results: list[dict]
    final_report: str
    sources: list[dict]

    # Control
    next_node: str
    error: str
