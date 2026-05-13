"""Agent progress visualization component for Streamlit."""

from __future__ import annotations

import streamlit as st


class AgentProgressDisplay:
    """Manages the real-time agent progress display in Streamlit."""

    def __init__(self):
        self._init_session_state()

    @staticmethod
    def _init_session_state():
        defaults = {
            "agent_steps": [],  # List of (step_type, details)
            "current_step": "",
            "research_plan": [],
            "retrieval_progress": {},
            "critique_results": [],
            "is_running": False,
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

    def handle_event(self, event_type: str, data: dict) -> None:
        """Route an SSE event to the appropriate handler."""
        handler = {
            "research_plan_start": self._on_plan_start,
            "research_plan_chunk": self._on_plan_chunk,
            "retrieval_start": self._on_retrieval_start,
            "retrieval_result": self._on_retrieval_result,
            "critique_start": self._on_critique_start,
            "critique_result": self._on_critique_result,
            "retry_triggered": self._on_retry_triggered,
            "synthesis_start": self._on_synthesis_start,
            "synthesis_chunk": self._on_synthesis_chunk,
            "done": self._on_done,
            "error": self._on_error,
        }.get(event_type)

        if handler:
            handler(data)
            st.session_state["agent_steps"].append((event_type, data))

    def _on_plan_start(self, data: dict) -> None:
        st.session_state["current_step"] = "planning"
        st.session_state["research_plan"] = []

    def _on_plan_chunk(self, data: dict) -> None:
        st.session_state["research_plan"].append({
            "index": data.get("index", 0),
            "question": data.get("question", ""),
            "strategy": data.get("strategy", ""),
        })

    def _on_retrieval_start(self, data: dict) -> None:
        st.session_state["current_step"] = "retrieving"
        st.session_state["retrieval_progress"] = {
            "step": data.get("step", 0),
            "total": data.get("total", 0),
            "strategy": data.get("strategy", ""),
            "retry": data.get("retry_count", 0),
        }

    def _on_retrieval_result(self, data: dict) -> None:
        st.session_state["retrieval_progress"]["results"] = data.get("result_count", 0)
        st.session_state["retrieval_progress"]["top_score"] = data.get("top_score", 0)

    def _on_critique_start(self, data: dict) -> None:
        st.session_state["current_step"] = "evaluating"

    def _on_critique_result(self, data: dict) -> None:
        st.session_state["critique_results"].append({
            "step": data.get("step", 0),
            "score": data.get("composite_score", 0),
            "passed": data.get("passed", False),
        })

    def _on_retry_triggered(self, data: dict) -> None:
        st.session_state["current_step"] = "retrying"

    def _on_synthesis_start(self, data: dict) -> None:
        st.session_state["current_step"] = "synthesizing"

    def _on_synthesis_chunk(self, data: dict) -> None:
        pass  # Report content handled by report_view

    def _on_done(self, data: dict) -> None:
        st.session_state["current_step"] = "done"
        st.session_state["is_running"] = False

    def _on_error(self, data: dict) -> None:
        st.session_state["current_step"] = "error"
        st.session_state["is_running"] = False


def render_progress_panel():
    """Render the agent progress visualization panel."""
    steps = st.session_state.get("agent_steps", [])
    current = st.session_state.get("current_step", "")
    plan = st.session_state.get("research_plan", [])
    critiques = st.session_state.get("critique_results", [])

    if not steps:
        return

    # Step indicators
    step_labels = {
        "planning": "📋 拆解问题",
        "retrieving": "🔍 检索中",
        "evaluating": "✅ 评估质量",
        "retrying": "🔄 重试检索",
        "synthesizing": "📝 生成报告",
        "done": "✨ 完成",
        "error": "❌ 错误",
    }
    status = step_labels.get(current, current)

    st.markdown(f"**当前状态**: {status}")

    # Research plan display
    if plan:
        st.markdown("**研究计划**:")
        for p in plan:
            strategy_icon = {"semantic": "🧠", "keyword": "🔑", "hybrid": "🔀"}.get(
                p.get("strategy", ""), "❓"
            )
            st.markdown(f"  {p['index']}. {strategy_icon} {p['question']}")

    # Critique results
    if critiques:
        st.markdown("**质量评估**:")
        for c in critiques[-3:]:  # show last 3
            status_icon = "✅" if c["passed"] else "⚠️"
            st.markdown(f"  {status_icon} 步骤 {c['step']}: 评分 {c['score']:.2f}")

    # Progress bar
    if current not in ("done", "error", ""):
        st.progress(0.0, text="Agent 思考中...")
