"""Streamlit frontend for Deep Research Agent."""

from __future__ import annotations

import os
import queue
import threading
import time

import httpx
import streamlit as st

from frontend.components.agent_progress import (
    AgentProgressDisplay,
    render_progress_panel,
)
from frontend.components.debug_drawer import render_debug_drawer
from frontend.components.report_view import render_sources
from frontend.components.empty_state import render_empty_state
from frontend.thread_worker import run_research_worker

BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Deep Research Agent",
    page_icon="🔬",
    layout="wide",
)

# Inject custom CSS
@st.cache_resource
def _load_css() -> str:
    css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        return f.read()

st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)

st.markdown(
    '<div class="app-header">'
    '<div class="app-title">🔬 Deep Research Agent</div>'
    '<div class="app-subtitle">Agentic RAG — 自主拆解问题 · 自适应检索 · 质量评估 · 报告合成</div>'
    "</div>",
    unsafe_allow_html=True,
)


# ── Initialize session state ──
_defaults = {
    "report": "",
    "is_running": False,
    "sources": [],
    "progress": AgentProgressDisplay(),
    "backend_error": "",
    "research_query": "",
    "_cancelled": False,
    "_streaming_report": "",
    "show_debug": False,
    "worker_thread": None,
    "event_queue": None,
    "cancel_event": None,
    "_task_id": None,
    "agent_steps": [],
    "research_plan": [],
    "critique_results": [],
    "progress_value": 0.0,
    "current_detail": "",
    "_chip_query": "",
    "cancel_requested": False,
    "_report_placeholder": None,
    "_research_counter": 0,
}
# Add pending submission flag to defaults
_defaults["_pending_submission"] = False

for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def _page_state() -> str:
    """Derive current page state from session."""
    # If we have a pending submission, always return "running"
    if st.session_state.get("_pending_submission"):
        return "running"
    if st.session_state["is_running"]:
        return "running"
    if st.session_state.get("_cancelled"):
        return "cancelled"
    if st.session_state["report"]:
        return "completed"
    return "idle"


def _drain_event_queue() -> str | None:
    """Consume all pending events from the worker queue.

    Returns an error message string if a backend_error event was received,
    otherwise None.
    """
    eq = st.session_state.get("event_queue")
    if eq is None:
        return None

    report_text = st.session_state.get("_streaming_report", "")
    error_msg = None
    events_processed = 0

    try:
        while True:
            event = eq.get_nowait()
            events_processed += 1
            event_type = event.get("event", "")
            data = event.get("data", {})

            if event_type == "_task_id":
                st.session_state["_task_id"] = data.get("task_id")

            elif event_type == "synthesis_chunk":
                text = data.get("text", "")
                report_text += text
                # Immediately update streaming report for real-time display
                st.session_state["_streaming_report"] = report_text

            elif event_type == "backend_error":
                error_msg = data.get("message", str(data))
                st.session_state["backend_error"] = error_msg

            elif event_type == "done":
                st.session_state["is_running"] = False
                if report_text:
                    st.session_state["report"] = report_text
                st.session_state["_streaming_report"] = ""
                task_id = st.session_state.get("_task_id")
                if task_id:
                    _fetch_final_result(task_id, report_text)

            elif event_type == "cancelled":
                st.session_state["_cancelled"] = True
                st.session_state["is_running"] = False

            # Always update progress (handles heartbeat filtering internally)
            st.session_state["progress"].handle_event(event_type, data)

    except queue.Empty:
        pass

    # Only update streaming state if still running — don't overwrite
    # the cleared state after done/cancelled events
    if not st.session_state.get("_cancelled") and st.session_state["report"] == "":
        st.session_state["_streaming_report"] = report_text
    # Debug: log events processed
    if events_processed > 0:
        print(f"[FRONTEND] _drain_event_queue: processed {events_processed} events, streaming_report len={len(report_text)}", flush=True)
    return error_msg


def _finalise_on_done():
    """Check if worker thread has died unexpectedly and finalise state."""
    worker = st.session_state.get("worker_thread")
    if worker is not None and not worker.is_alive():
        st.session_state["is_running"] = False
        streaming = st.session_state.get("_streaming_report", "")
        if streaming and not st.session_state["report"]:
            st.session_state["report"] = streaming
        st.session_state["_streaming_report"] = ""
        task_id = st.session_state.get("_task_id")
        if task_id and not st.session_state.get("sources"):
            _fetch_final_result(task_id, streaming or "")
        st.session_state["worker_thread"] = None


def _fetch_final_result(task_id: str, fallback_report: str):
    """Fetch final result including sources from backend."""
    import asyncio

    async def _fetch():
        async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as c:
            r = await c.get(f"{BACKEND_URL}/api/v1/research/{task_id}")
            return r

    try:
        resp = asyncio.run(_fetch())
        if resp.status_code == 200:
            body = resp.json()
            result = body.get("data", {}).get("result")
            if result:
                st.session_state["report"] = result.get(
                    "report", fallback_report
                )
                st.session_state["sources"] = result.get("sources", [])
    except Exception:
        if not st.session_state["report"]:
            st.session_state["report"] = fallback_report


# ── Example query chips ──
EXAMPLE_QUERIES = [
    "人工智能在医疗影像和药物研发中的应用有什么区别？",
    "Transformer架构相比LSTM在自然语言处理中有哪些优势？",
    "量子计算的发展对现代密码学构成多大的威胁？",
    "CRISPR基因编辑技术在遗传病治疗中的前景和伦理挑战是什么？",
    "固态电池技术相比传统锂电池的核心突破点在哪里？",
]

# ── Sync chip query before widget renders ──
if st.session_state.get("_chip_query"):
    st.session_state["research_query"] = st.session_state["_chip_query"]
    st.session_state["_chip_query"] = ""

# ── Search form ──
with st.form("search_form", clear_on_submit=False):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        query = st.text_area(
            "输入你的研究问题",
            placeholder="例如：人工智能在医疗影像和药物研发中的应用有什么区别？",
            height=60,
            key="research_query",
            disabled=st.session_state["is_running"],
            label_visibility="collapsed",
        )
    with col_btn:
        st.write("")
        submitted = st.form_submit_button(
            "🚀 开始",
            type="primary",
            use_container_width=True,
            disabled=st.session_state["is_running"],
        )

# ── Example query chips (outside form) ──
cols_chips = st.columns(len(EXAMPLE_QUERIES))
for i, (col, ex) in enumerate(zip(cols_chips, EXAMPLE_QUERIES)):
    with col:
        short_label = ex[:30] + "…" if len(ex) > 30 else ex
        if st.button(
            short_label,
            key=f"chip_{i}",
            use_container_width=True,
            disabled=st.session_state["is_running"],
            help=ex,
        ):
            st.session_state["_chip_query"] = ex
            st.rerun()

# ── Clear previous research on form submission ──
# This must happen BEFORE page_state is computed to avoid showing old content
if submitted and query.strip():
    # Explicitly clear old report DOM by calling .empty() on the previous placeholder.
    # This is more reliable than relying on Streamlit's React diff to clean up
    # raw HTML injected by st.markdown(unsafe_allow_html=True).
    old_placeholder = st.session_state.get("_report_placeholder")
    if old_placeholder is not None:
        old_placeholder.empty()
    st.session_state["_report_placeholder"] = None

    st.session_state["_last_submitted_task_id"] = st.session_state.get("_task_id")
    st.session_state["report"] = ""
    st.session_state["_streaming_report"] = ""
    st.session_state["sources"] = []
    st.session_state["_cancelled"] = False
    st.session_state["progress"] = AgentProgressDisplay()
    st.session_state["agent_steps"] = []
    st.session_state["research_plan"] = []
    st.session_state["critique_results"] = []
    st.session_state["backend_error"] = ""
    st.session_state["progress_value"] = 0.0
    st.session_state["current_detail"] = "准备中..."
    st.session_state["started_at"] = time.time()
    st.session_state["cancel_requested"] = False

    eq = queue.Queue()
    ce = threading.Event()
    thread = threading.Thread(
        target=run_research_worker,
        args=(query, eq, ce),
        daemon=True,
    )
    st.session_state["event_queue"] = eq
    st.session_state["cancel_event"] = ce
    st.session_state["worker_thread"] = thread
    st.session_state["_task_id"] = None
    st.session_state["is_running"] = True
    st.session_state["_pending_submission"] = True
    st.session_state["_research_counter"] = st.session_state.get("_research_counter", 0) + 1
    thread.start()
    st.session_state["_pending_submission"] = False
    st.rerun()

# Handle stop button AFTER potential form submission
if st.session_state.get("cancel_event") and st.session_state.get("cancel_event").is_set():
    # Already cancelled, nothing to do
    pass
elif "cancel_requested" in st.session_state and st.session_state["cancel_requested"]:
    st.session_state["cancel_requested"] = False
    ce = st.session_state.get("cancel_event")
    if ce:
        ce.set()
    st.session_state["_cancelled"] = True
    st.session_state["is_running"] = False
    streaming = st.session_state.get("_streaming_report", "")
    if streaming:
        st.session_state["report"] = streaming
    st.session_state["_streaming_report"] = ""
    st.rerun()

page_state = _page_state()

# ── Status bar (running) ──
if page_state == "running":
    _col_s, _col_btn_s = st.columns([6, 1])
    with _col_s:
        progress_val = st.session_state.get("progress_value", 0.0)
        current_detail = st.session_state.get("current_detail", "准备中...")
        started_at = st.session_state.get("started_at")
        elapsed_str = ""
        if started_at:
            elapsed_str = f"⏱ {int(time.time() - started_at)}s"
        st.markdown(
            f'<div class="status-bar">'
            f'<span class="status-bar-phase">{current_detail}</span>'
            f'<span class="status-bar-elapsed">{elapsed_str}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.progress(min(max(progress_val, 0.05), 0.98))
    with _col_btn_s:
        if st.button("🛑 停止", key="_stop_btn", use_container_width=True, type="secondary"):
            st.session_state["cancel_requested"] = True
            st.rerun()

# ── Cancelled notice ──
if page_state == "cancelled":
    st.warning("⚠️ 研究已被用户取消 — 已保留部分结果")

# ── Backend error ──
if st.session_state.get("backend_error"):
    st.error(st.session_state["backend_error"])
    st.info("请确保后端已启动: `uvicorn backend.main:app --reload`")

# ── Dynamic layout (always two columns so Streamlit reuses containers) ──
left, right = st.columns([1, 2])

with left:
    if page_state == "idle":
        # Empty left column in idle state for layout stability
        pass
    else:
        st.markdown('<p class="section-heading">🤖 Agent 思考过程</p>', unsafe_allow_html=True)
        with st.container():
            render_progress_panel()

with right:
    if page_state == "idle":
        render_empty_state()
    else:
        st.markdown('<p class="section-heading">📊 研究报告</p>', unsafe_allow_html=True)
        # Reuse or create a persistent st.empty() placeholder stored in session state.
        # On form submission, the old placeholder is explicitly cleared via .empty()
        # before a new one is created — this guarantees old report DOM nodes are removed
        # rather than relying on Streamlit's React diff (which may not clean up raw HTML
        # injected by st.markdown).
        report_placeholder = st.session_state.get("_report_placeholder")
        if report_placeholder is None:
            report_placeholder = st.empty()
            st.session_state["_report_placeholder"] = report_placeholder
        if page_state == "running":
            streaming = st.session_state.get("_streaming_report", "")
            if streaming:
                report_placeholder.markdown(streaming)
            else:
                report_placeholder.markdown("*Agent 正在准备报告...*")
        elif page_state == "completed":
            report = st.session_state.get("report", "")
            if report:
                report_placeholder.markdown(report)
            else:
                report_placeholder.markdown("*无报告内容。*")
        elif page_state == "cancelled":
            report = st.session_state.get("report", "")
            if report:
                report_placeholder.markdown(report)
            else:
                report_placeholder.markdown("*无报告内容。*")

        # Render sources separately (outside placeholder — they only show when completed)
        if page_state == "completed":
            sources = st.session_state.get("sources", [])
            if sources:
                render_sources(sources)

# ── Poll worker events when running ──
if st.session_state["is_running"]:
    _drain_event_queue()
    _finalise_on_done()

    if st.session_state["is_running"]:
        time.sleep(0.15)
        st.rerun()
    else:
        st.rerun()

# ── Debug drawer (hidden sidebar replacement) ──
render_debug_drawer()
