"""First-phase permission and retrieval isolation tests."""

from backend.auth import User, can_access_document
from research_agent.retrieval.bm25 import BM25Retriever


def test_document_visibility_policies(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    researcher = User("u1", "u1@example.com", "研究者", "researcher", "dept-a")

    assert can_access_document(researcher, {"upload_id": "public", "visibility": "public"})
    assert can_access_document(
        researcher,
        {"upload_id": "dept", "visibility": "department", "department_id": "dept-a"},
    )
    assert not can_access_document(
        researcher,
        {"upload_id": "other-dept", "visibility": "department", "department_id": "dept-b"},
    )
    assert can_access_document(
        researcher,
        {"upload_id": "role", "visibility": "roles", "allowed_roles": "researcher"},
    )
    assert can_access_document(
        researcher,
        {"upload_id": "departments", "visibility": "departments", "allowed_departments": ["dept-a", "dept-c"]},
    )
    assert not can_access_document(
        researcher,
        {"upload_id": "other-departments", "visibility": "departments", "allowed_departments": ["dept-b"]},
    )
    assert not can_access_document(
        researcher,
        {"upload_id": "private", "visibility": "private", "owner_id": "other"},
    )


def test_bm25_retrieval_filters_by_allowed_upload_ids():
    retriever = BM25Retriever()
    retriever.index_documents(
        ["a-1", "b-1", "c-1"],
        ["刘悦负责算法研究", "刘悦负责市场研究", "完全不同的文档"],
        [{"upload_id": "doc-a"}, {"upload_id": "doc-b"}, {"upload_id": "doc-c"}],
    )

    results = retriever.search("市场", top_k=5, allowed_upload_ids={"doc-b"})
    assert results
    assert {item.metadata["upload_id"] for item in results} == {"doc-b"}
