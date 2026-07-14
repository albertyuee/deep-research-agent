"""Integration tests for the agent graph state machine."""

import pytest
from research_agent.graph import _normalize_sub_queries, should_retry
from research_agent.planner.research_plan import ResearchPlan


class TestConditionalRouting:
    def test_should_retry_routes_to_retrieval_when_steps_remain(self):
        state = {
            "current_step": 1,
            "total_steps": 3,
        }
        result = should_retry(state)
        assert result == "retrieval"
        assert state["current_step"] == 1

    def test_should_retry_routes_to_synthesis_when_all_steps_done(self):
        state = {
            "current_step": 3,
            "total_steps": 3,
        }
        result = should_retry(state)
        assert result == "synthesis"

    def test_should_retry_is_pure_and_does_not_mutate_retry_state(self):
        state = {
            "current_step": 0,
            "total_steps": 3,
            "retry_count": 2,
            "low_confidence_steps": [],
        }
        result = should_retry(state)
        assert result == "retrieval"
        assert state["retry_count"] == 2
        assert state["low_confidence_steps"] == []


class TestState:
    def test_research_state_import(self):
        from research_agent.state import ResearchState
        state: ResearchState = {
            "query": "test",
            "current_step": 0,
            "total_steps": 1,
        }
        assert state["query"] == "test"


class TestResearchModeNormalization:
    @staticmethod
    def _plan():
        sub_queries = [
            {"index": 1, "question": "Q1", "strategy": "semantic", "hop": 1},
            {"index": 2, "question": "Q2", "strategy": "semantic", "hop": 1},
            {"index": 3, "question": "Q3", "strategy": "hybrid", "hop": 1},
        ]
        return sub_queries, ResearchPlan.from_decomposition("Q", sub_queries)

    def test_parallel_mode_clears_dependencies(self):
        sub_queries, plan = self._plan()
        plan.steps[1].depends_on = [1]

        normalized = _normalize_sub_queries(
            sub_queries, plan, "parallel", False, 3
        )

        assert all(step["hop"] == 1 for step in normalized)
        assert all(step["depends_on"] == [] for step in normalized)

    def test_multihop_mode_builds_a_dependency_chain(self):
        sub_queries, plan = self._plan()

        normalized = _normalize_sub_queries(
            sub_queries, plan, "multihop", True, 3
        )

        assert [step["depends_on"] for step in normalized] == [[], [1], [2]]
        assert [step["hop"] for step in normalized] == [1, 2, 3]

    def test_multihop_mode_respects_task_hop_limit(self):
        sub_queries, plan = self._plan()

        normalized = _normalize_sub_queries(
            sub_queries, plan, "multihop", True, 2
        )

        assert [step["hop"] for step in normalized] == [1, 2, 2]
