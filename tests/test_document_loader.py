"""Regression tests for document chunking and searchable text."""

from research_agent.retrieval.bm25 import BM25Retriever
from research_agent.retrieval.document_loader import DocumentLoader
from research_agent.retrieval.search_text import build_searchable_text


def test_short_identity_paragraphs_are_merged_instead_of_discarded():
    loader = DocumentLoader(min_chunk_length=50, max_chunk_chars=300)
    text = "\n\n".join(
        [
            "刘  悦",
            "AI Agent 开发工程师",
            "联系方式：" + "邮箱和电话" * 15,
            "核心项目",
            "基于 LangGraph 构建多智能体研究系统，支持检索、评价和报告生成。" * 2,
        ]
    )

    chunks = loader._chunk_text(
        text,
        source_path="resume.docx",
        file_name="刘悦_AI_Agent开发_简历.docx",
        file_type="docx",
    )

    assert "刘  悦" in chunks[0].content
    assert "AI Agent 开发工程师" in chunks[0].content
    assert "联系方式" in chunks[0].content
    assert "核心项目" in chunks[1].content


def test_trailing_short_paragraph_is_preserved():
    loader = DocumentLoader(min_chunk_length=50, max_chunk_chars=300)
    chunks = loader._chunk_text("这是正文。" * 15 + "\n\n附录")

    assert chunks
    assert chunks[-1].content.endswith("附录")


def test_searchable_text_normalizes_chinese_name_and_includes_title():
    searchable = build_searchable_text(
        "刘  悦\nAI Agent 开发工程师",
        {"file_name": "刘悦_AI_Agent开发_简历_新版.docx"},
    )

    assert "刘悦" in searchable
    assert "文档标题：刘悦 AI Agent开发简历新版" in searchable


def test_bm25_searches_document_title_but_returns_original_content():
    bm25 = BM25Retriever()
    original = "基于 LangGraph 构建多个智能体完成检索和报告生成。"
    bm25.index_documents(
        ["resume", "other", "third"],
        [original, "医疗影像诊断系统介绍", "药物发现与临床试验数据"],
        [
            {"doc_title": "刘悦 AI Agent 开发简历"},
            {"doc_title": "医疗人工智能"},
            {"doc_title": "药物研发"},
        ],
    )

    results = bm25.search("刘悦", top_k=2)

    assert results[0].chunk_id == "resume"
    assert results[0].content == original
