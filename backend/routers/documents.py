"""Document management API — upload, list, delete with auto-indexing."""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from research_agent.retrieval.document_loader import DocumentLoader, SUPPORTED_EXTENSIONS
from research_agent.retrieval.vector_store import create_vector_store
from research_agent.retrieval.bm25 import BM25Retriever

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path("data/uploads")
FILES_JSON = UPLOAD_DIR / "files.json"
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024
UPLOAD_READ_CHUNK_SIZE = 1024 * 1024
MAX_SAFE_FILENAME_LENGTH = 120

_vector_store = None
_bm25: BM25Retriever | None = None


def _get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = create_vector_store()
    return _vector_store


def _get_bm25() -> BM25Retriever:
    global _bm25
    if _bm25 is None:
        _bm25 = BM25Retriever()
    return _bm25


def _read_files_meta() -> dict:
    if not FILES_JSON.exists():
        return {"files": []}
    with open(FILES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_files_meta(data: dict) -> None:
    FILES_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(FILES_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _sanitize_filename(filename: str) -> str:
    """Return a storage-safe filename derived from user input."""
    name = PureWindowsPath(PurePosixPath(filename).name).name
    name = unicodedata.normalize("NFKC", name).strip()
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    name = re.sub(r"[^\w.\-]+", "_", name, flags=re.UNICODE)
    name = name.strip(" ._-")

    if not name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = Path(name)
    suffix = path.suffix
    stem = path.stem.strip(" ._-")
    if not stem or not suffix:
        raise HTTPException(status_code=400, detail="Invalid filename")

    max_stem_length = MAX_SAFE_FILENAME_LENGTH - len(suffix)
    if max_stem_length <= 0:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if len(stem) > max_stem_length:
        stem = stem[:max_stem_length].rstrip(" ._-")

    return f"{stem}{suffix.lower()}"


async def _save_upload_with_limit(file: UploadFile, destination: Path) -> int:
    """Save upload in chunks and reject files exceeding MAX_UPLOAD_SIZE_BYTES."""
    total_size = 0
    with open(destination, "wb") as f:
        while chunk := await file.read(UPLOAD_READ_CHUNK_SIZE):
            total_size += len(chunk)
            if total_size > MAX_UPLOAD_SIZE_BYTES:
                max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
                raise HTTPException(status_code=413, detail=f"File too large. Max upload size is {max_mb} MB")
            f.write(chunk)
    return total_size


class DocumentItem(BaseModel):
    id: str
    name: str
    size: int
    chunks: int
    status: str
    uploaded_at: str


class DocumentListResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


class DocumentUploadResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


class DocumentDeleteResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


def _scan_chroma_docs() -> list[dict]:
    """Discover documents from ChromaDB that are not in files.json."""
    try:
        vs = _get_vector_store()
        data = vs.collection.get(include=["metadatas"])
        if not data or not data["metadatas"]:
            return []

        # Group chunks by doc_title
        doc_groups: dict[str, dict] = {}
        for meta in data["metadatas"]:
            title = meta.get("doc_title") or meta.get("source") or meta.get("file_name", "unknown")
            if title not in doc_groups:
                doc_groups[title] = {
                    "name": title,
                    "chunks": 0,
                    "upload_id": meta.get("upload_id") or meta.get("source_path", ""),
                }
            doc_groups[title]["chunks"] += 1

        return [
            {
                "id": info["upload_id"][:12] if info["upload_id"] else uuid.uuid4().hex[:12],
                "name": name + ("" if "." in name else ".md"),
                "size": 0,
                "chunks": info["chunks"],
                "status": "ready",
                "uploaded_at": "",
            }
            for name, info in doc_groups.items()
        ]
    except Exception:
        return []


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """List all uploaded documents plus ChromaDB-indexed documents."""
    meta = _read_files_meta()
    all_files = list(meta["files"])

    # Supplement with ChromaDB documents not in files.json
    existing_names = {f["name"] for f in all_files}
    for doc in _scan_chroma_docs():
        if doc["name"] not in existing_names:
            all_files.append(doc)

    return DocumentListResponse(success=True, data={"files": all_files})


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document, chunk it, and index into vector + BM25 stores."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    safe_filename = _sanitize_filename(file.filename)
    ext = Path(safe_filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    file_id = uuid.uuid4().hex[:12]
    file_dir = UPLOAD_DIR / file_id
    file_dir.mkdir(parents=True, exist_ok=True)

    temp_path = file_dir / safe_filename

    try:
        file_size = await _save_upload_with_limit(file, temp_path)

        loader = DocumentLoader()
        chunks = loader.load_file(temp_path)

        if not chunks:
            raise HTTPException(status_code=400, detail="Document produced no chunks (may be too short or empty)")

        vs = _get_vector_store()
        chunk_ids = [c.chunk_id for c in chunks]
        chunk_texts = [c.content for c in chunks]
        chunk_metas = [
            {
                **c.metadata,
                "doc_title": Path(safe_filename).stem,
                "source": safe_filename,
                "upload_id": file_id,
            }
            for c in chunks
        ]
        vs.add_documents(chunk_ids, chunk_texts, chunk_metas)

        bm25 = _get_bm25()
        if bm25.is_indexed:
            all_ids = [bm25._documents[i]["id"] for i in range(len(bm25._documents))]
            all_texts = [bm25._documents[i]["content"] for i in range(len(bm25._documents))]
            all_metas = [bm25._documents[i]["metadata"] for i in range(len(bm25._documents))]
            all_ids.extend(chunk_ids)
            all_texts.extend(chunk_texts)
            all_metas.extend(chunk_metas)
        else:
            all_ids = chunk_ids
            all_texts = chunk_texts
            all_metas = chunk_metas
        bm25.index_documents(all_ids, all_texts, all_metas)

        meta = _read_files_meta()
        meta["files"].append({
            "id": file_id,
            "name": safe_filename,
            "size": file_size,
            "chunks": len(chunks),
            "status": "ready",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })
        _write_files_meta(meta)

        return DocumentUploadResponse(
            success=True,
            data={
                "file_id": file_id,
                "name": safe_filename,
                "chunks": len(chunks),
                "status": "ready",
            },
        )

    except HTTPException:
        if file_dir.exists():
            shutil.rmtree(file_dir)
        raise
    except Exception as e:
        if file_dir.exists():
            shutil.rmtree(file_dir)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.delete("/{file_id}", response_model=DocumentDeleteResponse)
async def delete_document(file_id: str):
    """Delete a document: remove original file, ChromaDB chunks, rebuild BM25."""
    meta = _read_files_meta()
    target = None
    for f in meta["files"]:
        if f["id"] == file_id:
            target = f
            break

    if not target:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        file_dir = UPLOAD_DIR / file_id
        if file_dir.exists():
            shutil.rmtree(file_dir)

        vs = _get_vector_store()
        try:
            vs.collection.delete(where={"upload_id": file_id})
        except Exception:
            pass

        try:
            remaining = vs.collection.get(include=["documents", "metadatas"])
            if remaining and remaining["ids"]:
                bm25 = _get_bm25()
                bm25.index_documents(
                    remaining["ids"],
                    remaining["documents"] or [],
                    remaining["metadatas"] or [],
                )
        except Exception:
            pass

        meta["files"] = [f for f in meta["files"] if f["id"] != file_id]
        _write_files_meta(meta)

        return DocumentDeleteResponse(
            success=True,
            data={"file_id": file_id, "message": "Document deleted"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
