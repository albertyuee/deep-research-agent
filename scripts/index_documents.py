"""One-click document indexing script.

Usage:
    python scripts/index_documents.py /path/to/docs
    python scripts/index_documents.py /path/to/docs --min-chunk-length 100
    python scripts/index_documents.py /path/to/docs --exclude "*.pdf"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index documents from a directory into Chroma vector store and BM25.",
    )
    parser.add_argument(
        "directory",
        help="Path to the directory containing documents to index.",
    )
    parser.add_argument(
        "--min-chunk-length",
        type=int,
        default=50,
        help="Minimum character length for a text chunk (default: 50).",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default=None,
        help='Glob pattern for files to exclude (e.g. "*.pdf").',
    )
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        print(f"Error: directory not found: {directory}")
        sys.exit(1)

    from research_agent.retrieval.document_loader import DocumentLoader
    from research_agent.retrieval.vector_store import create_vector_store
    from research_agent.retrieval.bm25 import BM25Retriever

    # 1. Load all documents
    loader = DocumentLoader(min_chunk_length=args.min_chunk_length)
    chunks = loader.load_directory(directory, exclude=args.exclude)

    if not chunks:
        print(f"Warning: no supported files found in {directory}")
        print(f"  Supported formats: .pdf, .docx, .md, .txt")
        sys.exit(0)

    # Count files
    file_names = sorted({c.metadata.get("file_name", "?") for c in chunks})
    print(f"Found {len(file_names)} file(s), {len(chunks)} chunk(s)")
    for fname in file_names:
        f_chunks = [c for c in chunks if c.metadata.get("file_name") == fname]
        print(f"  {fname}: {len(f_chunks)} chunks")

    # 2. Index to vector store
    vs = create_vector_store()
    print(f"  Backend: {vs.__class__.__name__}")
    chunk_ids = [c.chunk_id for c in chunks]
    texts = [c.content for c in chunks]
    # Add doc_title from file_name for citation display
    metadatas = [
        {
            **c.metadata,
            "doc_title": c.metadata.get("file_name", "").rsplit(".", 1)[0],
        }
        for c in chunks
    ]
    vs.add_documents(chunk_ids, texts, metadatas)
    print(f"  Vector store: {vs.count} documents total")

    # 3. Index to BM25
    print("Indexing to BM25...")
    bm25 = BM25Retriever()
    bm25.index_documents(chunk_ids, texts, metadatas)
    print(f"  BM25: {len(chunks)} documents indexed")

    print("\nDone.")


if __name__ == "__main__":
    main()
