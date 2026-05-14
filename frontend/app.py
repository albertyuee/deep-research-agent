"""Streamlit frontend for Deep Research Agent."""

from __future__ import annotations

import asyncio

import streamlit as st
import httpx

from frontend.components.agent_progress import AgentProgressDisplay, render_progress_panel
from frontend.components.report_view import render_report, render_sources

BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Deep Research Agent",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 Deep Research Agent")
st.caption("Agentic RAG — Agent 自主拆解问题、自适应检索、质量评估、合成研究报告")


# Initialize session state
if "report" not in st.session_state:
    st.session_state["report"] = ""
if "is_running" not in st.session_state:
    st.session_state["is_running"] = False
if "sources" not in st.session_state:
    st.session_state["sources"] = []
if "progress" not in st.session_state:
    st.session_state["progress"] = AgentProgressDisplay()
if "backend_error" not in st.session_state:
    st.session_state["backend_error"] = ""


# Input area
query = st.text_area(
    "输入你的研究问题",
    placeholder="例如：人工智能在医疗影像和药物研发中的应用有什么区别？",
    height=100,
    disabled=st.session_state["is_running"],
)

col1, col2 = st.columns([1, 5])
with col1:
    submit = st.button(
        "🚀 开始研究",
        type="primary",
        disabled=st.session_state["is_running"] or not query.strip(),
    )

if submit and query.strip():
    st.session_state["is_running"] = True
    st.session_state["report"] = ""
    st.session_state["sources"] = []
    st.session_state["progress"] = AgentProgressDisplay()
    st.session_state["agent_steps"] = []
    st.session_state["research_plan"] = []
    st.session_state["critique_results"] = []
    st.session_state["backend_error"] = ""
    st.rerun()


# Layout: progress panel (left) + report panel (right)
left, right = st.columns([1, 2])

with left:
    st.markdown("### 🤖 Agent 思考过程")
    progress_placeholder = st.empty()

with right:
    st.markdown("### 📊 研究报告")
    report_placeholder = st.empty()


# If running, connect to backend and stream events
if st.session_state["is_running"] and query.strip():
    async def run_research():
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            # Submit task
            try:
                resp = await client.post(
                    f"{BACKEND_URL}/api/v1/research",
                    json={"query": query},
                )
            except Exception as e:
                st.session_state["backend_error"] = f"无法连接后端: {e}"
                st.session_state["is_running"] = False
                return

            if resp.status_code != 200:
                st.session_state["backend_error"] = f"提交失败: {resp.text}"
                st.session_state["is_running"] = False
                return

            task_data = resp.json()
            task_id = task_data["data"]["task_id"]

            # Stream events
            url = f"{BACKEND_URL}/api/v1/research/{task_id}/stream"
            report_text = ""

            try:
                async with client.stream("GET", url, timeout=httpx.Timeout(600, connect=30)) as stream:
                    async for line in stream.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        import json
                        try:
                            event = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue

                        event_type = event.get("event", "")
                        data = event.get("data", {})

                        # Handle synthesis chunks
                        if event_type == "synthesis_chunk":
                            report_text += data.get("text", "")
                            report_placeholder.markdown(report_text)

                        # Update progress
                        st.session_state["progress"].handle_event(event_type, data)

                        with progress_placeholder.container():
                            render_progress_panel()

                        # Capture sources
                        if event_type == "done":
                            # Fetch final result
                            try:
                                status_resp = await client.get(
                                    f"{BACKEND_URL}/api/v1/research/{task_id}"
                                )
                                if status_resp.status_code == 200:
                                    body = status_resp.json()
                                    result = body.get("data", {}).get("result")
                                    if result:
                                        st.session_state["report"] = result.get("report", report_text)
                                        report_placeholder.markdown(st.session_state["report"])
                                        st.session_state["sources"] = result.get("sources", [])
                            except Exception:
                                st.session_state["report"] = report_text
                                report_placeholder.markdown(report_text)

                            st.session_state["is_running"] = False
                            with progress_placeholder.container():
                                render_progress_panel()
                            return

            except asyncio.TimeoutError:
                st.session_state["backend_error"] = "研究超时（600 秒），请检查后端日志"
            except httpx.ReadTimeout:
                st.session_state["backend_error"] = "SSE 连接读取超时 — Agent 可能仍在后台运行，请稍后查看结果"
            except httpx.ConnectTimeout:
                st.session_state["backend_error"] = "SSE 连接超时 — 请确认后端已启动"
            except Exception as e:
                err_msg = str(e) or type(e).__name__
                st.session_state["backend_error"] = f"SSE 连接中断: {err_msg}"

            st.session_state["is_running"] = False

    try:
        asyncio.run(run_research())
    except Exception as e:
        st.session_state["backend_error"] = f"连接后端失败: {e}"
        st.session_state["is_running"] = False

# Show backend error if any
if st.session_state.get("backend_error"):
    st.error(st.session_state["backend_error"])
    st.info("请确保后端已启动: `uvicorn backend.main:app --reload`")

# If running, do one final render of progress after async completes
if st.session_state["is_running"]:
    with progress_placeholder.container():
        render_progress_panel()
