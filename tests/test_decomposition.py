"""Tests for query decomposition module."""

import pytest
from research_agent.planner.research_plan import ResearchPlan, ResearchStep


class TestResearchPlan:
    def test_from_decomposition_single_query(self):
        sub_queries = [
            {"index": 1, "question": "什么是RAG？", "strategy": "semantic", "rationale": "概念性问题"}
        ]
        plan = ResearchPlan.from_decomposition("什么是RAG？", sub_queries)
        assert plan.step_count == 1
        assert plan.original_query == "什么是RAG？"

    def test_from_decomposition_multi_query(self):
        sub_queries = [
            {"index": 1, "question": "Q1", "strategy": "semantic", "rationale": ""},
            {"index": 2, "question": "Q2", "strategy": "keyword", "rationale": ""},
            {"index": 3, "question": "Q3", "strategy": "hybrid", "rationale": ""},
        ]
        plan = ResearchPlan.from_decomposition("复杂问题", sub_queries)
        assert plan.step_count == 3

    def test_get_step(self):
        sub_queries = [
            {"index": 1, "question": "Q1", "strategy": "hybrid", "rationale": ""},
            {"index": 2, "question": "Q2", "strategy": "hybrid", "rationale": ""},
        ]
        plan = ResearchPlan.from_decomposition("test", sub_queries)
        step = plan.get_step(1)
        assert step is not None
        assert step.sub_query == "Q1"

    def test_get_step_missing(self):
        plan = ResearchPlan(original_query="test", steps=[])
        assert plan.get_step(99) is None

    def test_step_strategy_preserved(self):
        sub_queries = [
            {"index": 1, "question": "Q", "strategy": "keyword", "rationale": "术语查询"}
        ]
        plan = ResearchPlan.from_decomposition("test", sub_queries)
        assert plan.steps[0].strategy == "keyword"
