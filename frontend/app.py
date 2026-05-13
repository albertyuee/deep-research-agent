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
    st.rerun()


# Layout: progress panel (left) + report panel (right)
left, right = st.columns([1, 2])

with left:
    st.markdown("### 🤖 Agent 思考过程")
    progress_placeholder = st.empty()

    if st.session_state["is_running"]:
        progress_placeholder.info("Agent 正在运行... 请查看右侧报告区等待结果")

with right:
    st.markdown("### 📊 研究报告")
    report_placeholder = st.empty()


# If running, connect to backend and stream events
if st.session_state["is_running"] and query.strip():
    async def run_research():
        async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
            # Submit task
            resp = await client.post(
                f"{BACKEND_URL}/api/v1/research",
                json={"query": query},
            )
            if resp.status_code != 200:
                st.error(f"提交失败: {resp.text}")
                st.session_state["is_running"] = False
                return

            task_data = resp.json()
            task_id = task_data["data"]["task_id"]

            # Stream events
            url = f"{BACKEND_URL}/api/v1/research/{task_id}/stream"
            report_text = ""

            async with client.stream("GET", url, timeout=httpx.Timeout(300)) as stream:
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
                        status_resp = await client.get(
                            f"{BACKEND_URL}/api/v1/research/{task_id}"
                        )
                        if status_resp.status_code == 200:
                            result = status_resp.json()["data"]["result"]
                            if result:
                                st.session_state["report"] = result.get("report", report_text)
                                report_placeholder.markdown(st.session_state["report"])
                                st.session_state["sources"] = result.get("sources", [])

                        st.session_state["is_running"] = False

                        with progress_placeholder.container():
                            render_progress_panel()
                        break

    try:
        asyncio.run(run_research())
    except Exception as e:
        st.error(f"连接后端失败: {e}")
        st.info("请确保后端已启动: `uvicorn backend.main:app --reload`")
        st.session_state["is_running"] = False
