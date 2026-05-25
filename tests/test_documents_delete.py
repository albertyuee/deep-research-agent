"""Tests for document deletion consistency."""

from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from backend.routers import documents
from research_agent.retrieval.bm25 import BM25Retriever


FILE_ID = "abc123def456"


def _prepare_document(tmp_path, monkeypatch, chunks: int = 2):
    upload_dir = tmp_path / "uploads"
    files_json = upload_dir / "files.json"
    file_dir = upload_dir / FILE_ID
    file_dir.mkdir(parents=True)
    (file_dir / "doc.md").write_text("test document", encoding="utf-8")
    files_json.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "id": FILE_ID,
                        "name": "doc.md",
                        "size": 13,
                        "chunks": chunks,
                        "status": "ready",
                        "uploaded_at": "2026-05-25T12:00:00+00:00",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(documents, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(documents, "FILES_JSON", files_json)
    monkeypatch.setattr(documents, "_bm25", BM25Retriever())
    return upload_dir, files_json, file_dir


@pytest.mark.asyncio
async def test_delete_document_fails_when_vector_delete_fails(tmp_path, monkeypatch):
    _, files_json, file_dir = _prepare_document(tmp_path, monkeypatch)

    class FailingVectorStore:
        def delete_by_upload_id(self, upload_id: str) -> int:
            raise RuntimeError("vector delete failed")

    monkeypatch.setattr(documents, "_get_vector_store", lambda: FailingVectorStore())

    with pytest.raises(HTTPException) as exc_info:
        await documents.delete_document(FILE_ID)

    assert exc_info.value.status_code == 500
    assert "Failed to delete vector chunks" in exc_info.value.detail
    assert file_dir.exists()
    assert json.loads(files_json.read_text(encoding="utf-8"))["files"][0]["id"] == FILE_ID


@pytest.mark.asyncio
async def test_delete_document_fails_when_no_chunks_are_deleted(tmp_path, monkeypatch):
    _, files_json, file_dir = _prepare_document(tmp_path, monkeypatch, chunks=2)

    class EmptyDeleteVectorStore:
        def delete_by_upload_id(self, upload_id: str) -> int:
            return 0

    monkeypatch.setattr(documents, "_get_vector_store", lambda: EmptyDeleteVectorStore())

    with pytest.raises(HTTPException) as exc_info:
        await documents.delete_document(FILE_ID)

    assert exc_info.value.status_code == 500
    assert "No vector chunks deleted" in exc_info.value.detail
    assert file_dir.exists()
    assert json.loads(files_json.read_text(encoding="utf-8"))["files"][0]["id"] == FILE_ID


@pytest.mark.asyncio
async def test_delete_document_removes_files_after_vector_delete_and_bm25_rebuild(tmp_path, monkeypatch):
    _, files_json, file_dir = _prepare_document(tmp_path, monkeypatch)

    class SuccessfulVectorStore:
        def delete_by_upload_id(self, upload_id: str) -> int:
            assert upload_id == FILE_ID
            return 2

        def get_all_documents(self):
            return ["remaining_1"], ["remaining text"], [{"upload_id": "other"}]

    monkeypatch.setattr(documents, "_get_vector_store", lambda: SuccessfulVectorStore())

    response = await documents.delete_document(FILE_ID)

    assert response.success is True
    assert response.data["deleted_chunks"] == 2
    assert response.data["indexed_chunks"] == 1
    assert not file_dir.exists()
    assert json.loads(files_json.read_text(encoding="utf-8"))["files"] == []
    assert documents._get_bm25().is_indexed
