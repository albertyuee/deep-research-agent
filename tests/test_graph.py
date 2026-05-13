"""Integration tests for the agent graph state machine."""

import pytest
from research_agent.graph import should_retry


class TestConditionalRouting:
    def test_should_retry_passed_advances(self):
        state = {
            "current_step": 0,
            "total_steps": 3,
            "critique_passed": True,
            "retry_count": 0,
            "all_retrieval_results": [],
            "all_critique_results": [],
            "retrieval_results": [{"chunk_id": "1", "content": "test", "score": 0.8}],
            "critique_result": {"composite_score": 0.8},
            "retry_history": [],
            "low_confidence_steps": [],
        }
        result = should_retry(state)
        assert result == "retrieval"  # more steps remain
        assert state["current_step"] == 1
        assert state["retry_count"] == 0

    def test_should_retry_passed_last_step_goes_to_synthesis(self):
        state = {
            "current_step": 2,
            "total_steps": 3,
            "critique_passed": True,
            "retry_count": 0,
            "all_retrieval_results": [],
            "all_critique_results": [],
            "retrieval_results": [{"chunk_id": "1", "content": "test", "score": 0.8}],
            "critique_result": {"composite_score": 0.8},
            "retry_history": [],
            "low_confidence_steps": [],
        }
        result = should_retry(state)
        assert result == "synthesis"

    def test_should_retry_failed_can_retry(self):
        state = {
            "current_step": 0,
            "total_steps": 3,
            "critique_passed": False,
            "retry_count": 0,
            "retrieval_results": [],
            "critique_result": {"composite_score": 0.4},
            "all_retrieval_results": [],
            "all_critique_results": [],
            "retry_history": [],
            "low_confidence_steps": [],
        }
        result = should_retry(state)
        assert result == "retrieval"
        assert state["retry_count"] == 1

    def test_should_retry_exhausted_advances(self):
        state = {
            "current_step": 1,
            "total_steps": 3,
            "critique_passed": False,
            "retry_count": 2,  # max = 3, so 2 means 3rd attempt failed
            "retrieval_results": [],
            "critique_result": {"composite_score": 0.4},
            "all_retrieval_results": [],
            "all_critique_results": [],
            "retry_history": [],
            "low_confidence_steps": [],
        }
        result = should_retry(state)
        assert result == "retrieval"  # more steps, goes back to retrieval for next step
        assert state["current_step"] == 2
        assert state["low_confidence_steps"] == [2]  # step+1

    def test_should_retry_exhausted_last_step_goes_to_synthesis(self):
        state = {
            "current_step": 2,
            "total_steps": 3,
            "critique_passed": False,
            "retry_count": 2,
            "retrieval_results": [],
            "critique_result": {"composite_score": 0.4},
            "all_retrieval_results": [],
            "all_critique_results": [],
            "retry_history": [],
            "low_confidence_steps": [],
        }
        result = should_retry(state)
        assert result == "synthesis"
        assert state["low_confidence_steps"] == [3]


class TestState:
    def test_research_state_import(self):
        from research_agent.state import ResearchState
        state: ResearchState = {
            "query": "test",
            "current_step": 0,
            "total_steps": 1,
        }
        assert state["query"] == "test"
