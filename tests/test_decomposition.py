"""Tests for query decomposition module."""

import pytest
from research_agent.planner.research_plan import ResearchPlan, ResearchStep
from research_agent.planner.decomposer import _build_system_prompt


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

    def test_multihop_dependency_is_preserved(self):
        sub_queries = [
            {
                "index": 1,
                "question": "识别关键方法",
                "strategy": "hybrid",
                "hop": 1,
                "depends_on": [],
            },
            {
                "index": 2,
                "question": "研究关键方法的应用",
                "strategy": "semantic",
                "hop": 2,
                "depends_on": [1],
                "input_slots": ["entities"],
                "terminal": True,
            },
        ]

        plan = ResearchPlan.from_decomposition("多跳问题", sub_queries)

        assert plan.steps[1].hop == 2
        assert plan.steps[1].depends_on == [1]
        assert plan.steps[1].input_slots == ["entities"]
        assert plan.steps[1].terminal is True

    def test_hop_infers_previous_dependency(self):
        plan = ResearchPlan.from_decomposition(
            "多跳问题",
            [{"index": 2, "question": "第二跳", "hop": 2}],
        )

        assert plan.steps[0].depends_on == [1]


class TestResearchModePrompts:
    def test_parallel_mode_requires_independent_steps(self):
        prompt = _build_system_prompt(research_mode="parallel", max_hops=3)

        assert "所有步骤必须互相独立" in prompt
        assert "depends_on=[]" in prompt

    def test_multihop_mode_requires_dependency(self):
        prompt = _build_system_prompt(research_mode="multihop", max_hops=4)

        assert "至少生成一条依赖关系" in prompt
        assert "最大允许跳数为 4" in prompt

    def test_step_text_must_be_chinese(self):
        prompt = _build_system_prompt(research_mode="auto", max_hops=3)

        assert "question 和 rationale 必须使用简体中文" in prompt
