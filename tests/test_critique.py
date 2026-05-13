"""Tests for quality critique module."""

import pytest
from research_agent.critique.retry_controller import RetryState, RetryAction


class TestRetryState:
    def test_initial_state(self):
        state = RetryState(max_retries=3)
        assert state.retry_count == 0
        assert state.can_retry()

    def test_can_retry_after_attempts(self):
        state = RetryState(max_retries=3, retry_count=2)
        assert state.can_retry()

    def test_cannot_retry_when_exhausted(self):
        state = RetryState(max_retries=3, retry_count=3)
        assert not state.can_retry()

    def test_exhausted(self):
        state = RetryState(max_retries=3, retry_count=3)
        assert state.exhausted()

    def test_not_exhausted(self):
        state = RetryState(max_retries=3, retry_count=1)
        assert not state.exhausted()

    def test_next_action_progression(self):
        """Verify retry actions escalate correctly."""
        state = RetryState(max_retries=3)

        # 1st retry: broaden
        action1 = state.next_action()
        assert action1["type"] == "broaden"
        state.retry_count = 1

        # 2nd retry: switch strategy
        action2 = state.next_action()
        assert action2["type"] == "switch_strategy"
        state.retry_count = 2

        # 3rd retry: rephrase
        action3 = state.next_action()
        assert action3["type"] == "rephrase"

    def test_record_attempt(self):
        from dataclasses import dataclass

        @dataclass
        class MockCritique:
            composite_score: float = 0.65
            reasoning: str = "ok"

        state = RetryState(max_retries=3)
        state.record_attempt({"type": "broaden"}, MockCritique())

        assert state.retry_count == 1
        assert len(state.history) == 1
        assert state.history[0]["attempt"] == 1
        assert state.history[0]["score"] == 0.65


class TestCritiqueResult:
    def test_critique_result_fields(self):
        from research_agent.critique.scorer import CritiqueResult

        result = CritiqueResult(
            composite_score=0.72,
            relevance_score=0.8,
            completeness_score=0.6,
            passed=True,
        )
        assert result.passed
        assert result.composite_score == 0.72

    def test_below_threshold_not_passed(self):
        from research_agent.critique.scorer import CritiqueResult

        result = CritiqueResult(
            composite_score=0.45,
            relevance_score=0.4,
            completeness_score=0.5,
            passed=False,
            retry_suggestion="扩大检索范围",
        )
        assert not result.passed
        assert result.retry_suggestion is not None
