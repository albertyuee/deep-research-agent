"""Integration tests for the agent graph state machine."""

import pytest
from research_agent.graph import should_retry


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
