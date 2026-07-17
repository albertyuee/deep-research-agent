"""Safely reindex uploaded documents with the latest chunking rules.

New versioned chunks are inserted before old chunks are removed, so a failed
embedding or insert operation leaves the existing searchable data untouched.

Usage:
    python scripts/reindex_uploads.py
    python scripts/reindex_uploads.py --upload-id 22c765a270d6
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
FILES_JSON = UPLOAD_DIR / "files.json"


def _write_files_meta(data: dict) -> None:
    temporary = FILES_JSON.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(FILES_JSON)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reindex uploaded knowledge-base documents")
    parser.add_argument("--upload-id", help="Only reindex this upload ID")
    parser.add_argument("--force", action="store_true", help="Reindex documents already on the latest version")
    args = parser.parse_args()

    if not FILES_JSON.exists():
        raise SystemExit(f"Upload metadata not found: {FILES_JSON}")

    from research_agent.retrieval.document_loader import DocumentLoader
    from research_agent.retrieval.search_text import INDEX_VERSION
    from research_agent.retrieval.vector_store import create_vector_store

    data = json.loads(FILES_JSON.read_text(encoding="utf-8"))
    targets = [
        item for item in data.get("files", [])
        if not args.upload_id or item.get("id") == args.upload_id
    ]
    if not targets:
        raise SystemExit(f"Upload not found: {args.upload_id}")

    store = create_vector_store()
    loader = DocumentLoader()

    for item in targets:
        upload_id = item["id"]
        file_path = UPLOAD_DIR / upload_id / item["name"]
        if not file_path.exists():
            print(f"SKIP {item['name']}: file is missing")
            continue

        all_ids, _, all_metadatas = store.get_all_documents()
        old_ids = [
            chunk_id for chunk_id, metadata in zip(all_ids, all_metadatas)
            if metadata.get("upload_id") == upload_id
        ]
        old_versions = {
            int(metadata.get("index_version") or 1)
            for metadata in all_metadatas
            if metadata.get("upload_id") == upload_id
        }
        if old_ids and old_versions == {INDEX_VERSION} and not args.force:
            print(f"SKIP {item['name']}: already at index version {INDEX_VERSION}")
            continue

        chunks = loader.load_file(file_path)
        if not chunks:
            print(f"SKIP {item['name']}: document produced no chunks")
            continue

        new_ids = [
            f"{file_path.stem}_v{INDEX_VERSION}_chunk_{index}"
            for index in range(len(chunks))
        ]
        texts = [chunk.content for chunk in chunks]
        metadatas = [
            {
                **chunk.metadata,
                "chunk_index": index,
                "doc_title": file_path.stem,
                "source": file_path.name,
                "upload_id": upload_id,
                "index_version": INDEX_VERSION,
            }
            for index, chunk in enumerate(chunks)
        ]

        print(f"REINDEX {item['name']}: {len(old_ids)} -> {len(new_ids)} chunks")
        store.add_documents(new_ids, texts, metadatas)
        try:
            deleted = store.delete_by_chunk_ids(old_ids)
        except Exception:
            store.delete_by_chunk_ids(new_ids)
            raise

        item["chunks"] = len(new_ids)
        item["status"] = "ready"
        item["index_version"] = INDEX_VERSION
        _write_files_meta(data)
        print(f"DONE {item['name']}: removed {deleted} old chunks")

    print("Reindex complete. Restart the backend to rebuild its in-memory BM25 index.")


if __name__ == "__main__":
    main()
