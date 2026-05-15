"""Report rendering component for Streamlit."""

from __future__ import annotations

import streamlit as st


def _score_badge(score: float) -> str:
    """Generate a colored badge for the score."""
    if score >= 0.7:
        color = "#10b981"
        bg = "#d1fae5"
    elif score >= 0.4:
        color = "#f59e0b"
        bg = "#fef3c7"
    else:
        color = "#ef4444"
        bg = "#fee2e2"
    return f'<span style="background:{bg}; color:{color}; padding:2px 8px; border-radius:12px; font-size:0.8rem; font-weight:600;">{score:.2f}</span>'


def render_sources(sources: list[dict]):
    """Render source citations list."""
    if not sources:
        return

    st.markdown("---")
    st.markdown("### 📎 引用来源")

    seen = set()
    for i, src in enumerate(sources):
        chunk_id = src.get("chunk_id", f"unknown_{i}")
        if chunk_id in seen:
            continue
        seen.add(chunk_id)

        score = src.get("score", src.get("combined_score", 0))
        meta = src.get("metadata", {})
        doc_title = meta.get("doc_title", meta.get("source", chunk_id))
        strategy = meta.get("strategy", "unknown")
        content = src.get("content", "")

        badge = _score_badge(score)
        preview = content[:150] + "..." if len(content) > 150 else content

        # Render as a styled card
        st.markdown(
            f"""
            <div class="source-card">
                <div class="source-header">
                    <span class="source-title">{doc_title}</span>
                    {badge}
                    <span class="source-strategy">{strategy}</span>
                </div>
                <p class="source-preview">{preview}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
