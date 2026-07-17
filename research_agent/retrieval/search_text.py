"""Build normalized text for vector and keyword retrieval."""

from __future__ import annotations

import re
from pathlib import Path


INDEX_VERSION = 2


def normalize_search_text(text: str) -> str:
    """Normalize formatting differences that should not affect retrieval."""
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def document_title(metadata: dict | None) -> str:
    """Return a human-readable document title from retrieval metadata."""
    metadata = metadata or {}
    raw_title = (
        metadata.get("doc_title")
        or metadata.get("file_name")
        or metadata.get("source")
        or ""
    )
    title = Path(str(raw_title)).stem
    title = re.sub(r"[_-]+", " ", title)
    return normalize_search_text(title)


def build_searchable_text(content: str, metadata: dict | None = None) -> str:
    """Combine document identity with content without changing displayed text."""
    normalized_content = normalize_search_text(content)
    title = document_title(metadata)
    if not title or title in normalized_content:
        return normalized_content
    return f"文档标题：{title}\n\n{normalized_content}"
