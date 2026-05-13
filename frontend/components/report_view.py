"""Report rendering component for Streamlit."""

from __future__ import annotations

import streamlit as st


def render_report(report: str):
    """Render the final research report in markdown."""
    if not report:
        return

    st.markdown("---")
    st.markdown("## 📄 研究报告")
    st.markdown(report)


def render_sources(sources: list[dict]):
    """Render source citations list."""
    if not sources:
        return

    with st.expander("📎 引用来源", expanded=False):
        seen = set()
        for i, src in enumerate(sources):
            chunk_id = src.get("chunk_id", f"unknown_{i}")
            if chunk_id in seen:
                continue
            seen.add(chunk_id)

            score = src.get("score", src.get("combined_score", 0))
            meta = src.get("metadata", {})
            doc_title = meta.get("doc_title", meta.get("source", chunk_id))

            st.markdown(
                f"**{doc_title}** — 得分: {score:.2f} | 策略: {meta.get('strategy', 'unknown')}"
            )
            with st.expander(f"预览: {src.get('content', '')[:100]}..."):
                st.text(src.get("content", ""))
