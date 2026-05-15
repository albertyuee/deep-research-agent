"""Debug panel component — inline toggleable panel replacing st.sidebar."""

from __future__ import annotations

import streamlit as st

from frontend.components.agent_progress import (
    _render_event_log,
    _render_timing_stats,
    _render_retry_history,
)


def render_debug_drawer():
    """Render a compact toggle button and the debug panel below it."""

    show = st.session_state.get("show_debug", False)

    # Toggle row: right-aligned compact pill button
    _, btn_col = st.columns([10, 1])
    with btn_col:
        label = "🔧 关闭调试" if show else "🔧 调试"
        if st.button(label, key="_debug_toggle_btn", use_container_width=True):
            st.session_state["show_debug"] = not show
            st.rerun()

    if not show:
        return

    st.markdown('<div class="debug-section">', unsafe_allow_html=True)
    st.markdown('<p class="section-heading">📋 调试面板</p>', unsafe_allow_html=True)

    tab_timing, tab_retry, tab_events = st.tabs(
        ["⏱ 阶段耗时", "🔄 重试记录", "📜 事件日志"]
    )

    with tab_timing:
        _render_timing_stats()

    with tab_retry:
        _render_retry_history()

    with tab_events:
        _render_event_log()

    st.markdown("</div>", unsafe_allow_html=True)
