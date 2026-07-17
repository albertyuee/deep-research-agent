"""Integration tests for the agent graph state machine."""

import asyncio

import pytest
from research_agent import graph as graph_module
from research_agent.graph import (
    _cap_sub_queries,
    _normalize_sub_queries,
    _research_step_progress,
    _retry_top_k,
    research_node,
    should_retry,
)
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


class TestResearchProgress:
    def test_progress_is_monotonic_across_steps(self):
        progress = [
            _research_step_progress(step, 3, fraction)
            for step in range(3)
            for fraction in (0.0, 0.45, 0.60, 0.65, 0.75, 1.0)
        ]

        assert progress == sorted(progress)
        assert progress[0] == pytest.approx(0.10)
        assert progress[-1] == pytest.approx(0.60)


class TestResearchLimits:
    def test_sub_queries_are_capped_at_three(self, monkeypatch):
        monkeypatch.setattr(graph_module.settings.reasoning, "max_sub_queries", 3)
        queries = [{"index": index} for index in range(1, 6)]

        assert [item["index"] for item in _cap_sub_queries(queries)] == [1, 2, 3]

    def test_retry_top_k_never_exceeds_twenty(self, monkeypatch):
        monkeypatch.setattr(graph_module.settings.retrieval, "top_k", 10)
        monkeypatch.setattr(graph_module.settings.retrieval, "retry_top_k_multiplier", 2)
        monkeypatch.setattr(graph_module.settings.retrieval, "max_top_k", 20)

        assert [_retry_top_k(attempt) for attempt in range(4)] == [10, 20, 20, 20]


@pytest.mark.asyncio
async def test_research_node_runs_dependency_layers_with_concurrency_two(monkeypatch):
    active = 0
    peak_active = 0
    layer_events = []

    async def fake_step(state, step_idx, semaphore):
        nonlocal active, peak_active
        async with semaphore:
            active += 1
            peak_active = max(peak_active, active)
            await asyncio.sleep(0.02)
            active -= 1
            branch = dict(state)
            step_number = step_idx + 1
            branch["completed_steps"] = [*state.get("completed_steps", []), step_number]
            branch["step_results"] = {**state.get("step_results", {}), str(step_number): []}
            branch["step_critiques"] = {**state.get("step_critiques", {}), str(step_number): {}}
            branch["retry_history"] = []
            branch["reasoning_paths"] = [[step_number]]
            branch["low_confidence_steps"] = []
            return step_idx, branch

    def capture_event(_task_id, event_type, data=None):
        if event_type == "research_layer_start":
            layer_events.append(data["steps"])

    monkeypatch.setattr(graph_module, "_run_research_step", fake_step)
    monkeypatch.setattr(graph_module, "emit", capture_event)
    monkeypatch.setattr(graph_module.settings.retrieval, "max_concurrency", 2)

    state = {
        "task_id": "",
        "sub_queries": [
            {"index": 1, "hop": 1, "depends_on": []},
            {"index": 2, "hop": 1, "depends_on": []},
            {"index": 3, "hop": 2, "depends_on": [1]},
        ],
        "max_hops": 3,
        "completed_steps": [],
        "low_confidence_steps": [],
        "step_results": {},
        "step_critiques": {},
    }

    result = await research_node(state)

    assert peak_active == 2
    assert layer_events == [[1, 2], [3]]
    assert result["completed_steps"] == [1, 2, 3]


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
