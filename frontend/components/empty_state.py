"""Empty state guide component for the report panel."""

from __future__ import annotations

import streamlit as st


def render_empty_state():
    """Render the welcome guide when no research is running and no report exists."""

    examples = [
        "人工智能在医疗影像和药物研发中的应用有什么区别？",
        "Transformer架构相比LSTM在自然语言处理中有哪些优势？",
        "量子计算的发展对现代密码学构成多大的威胁？",
        "CRISPR基因编辑技术在遗传病治疗中的前景和伦理挑战是什么？",
        "固态电池技术相比传统锂电池的核心突破点在哪里？",
    ]

    html = (
        '<div class="welcome-wrapper">'
        '<div class="welcome-container">'
        '<div class="welcome-icon">🔬</div>'
        '<div class="welcome-title">欢迎使用 Deep Research Agent</div>'
        '<div class="welcome-subtitle">'
        '基于 Agentic RAG 的自主深度研究助手<br>'
        'Agent 自动拆解问题 · 自适应检索 · 评估质量 · 合成报告'
        '</div>'
        "</div>"
        '<div class="steps-row">'
        '<div class="step-card">'
        '<div class="step-number">1</div>'
        "<h4>📝 输入研究问题</h4>"
        "<p>输入你想深入研究的任何问题</p>"
        "</div>"
        '<div class="step-card">'
        '<div class="step-number">2</div>'
        "<h4>🤖 Agent 自主研究</h4>"
        "<p>自动拆解→检索→评估→重试→合成</p>"
        "</div>"
        '<div class="step-card">'
        '<div class="step-number">3</div>'
        "<h4>📊 获取研究报告</h4>"
        "<p>结构化报告 + 可追溯引用来源</p>"
        "</div>"
        "</div>"
        '<div class="examples-section">'
        '<h3>💡 试试这些问题</h3>'
    )

    for ex in examples:
        html += f'<div class="example-item">{ex}</div>'

    html += "</div></div>"

    st.markdown(html, unsafe_allow_html=True)
