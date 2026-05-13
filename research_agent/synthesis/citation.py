from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Citation:
    source_id: str
    doc_title: str
    chunk_index: int = 0
    score: float = 0.0
    strategy: str = "unknown"


def format_citation(c: Citation) -> str:
    """Format a citation as inline markdown."""
    return f"[来源: {c.doc_title}, chunk_{c.chunk_index}, score={c.score:.2f}]"


def build_citation_map(sources: list[dict]) -> dict[str, Citation]:
    """Build a lookup map from chunk_id to Citation.

    Args:
        sources: List of source dicts from retrieval results.

    Returns:
        Dict mapping chunk_id to Citation object.
    """
    citation_map: dict[str, Citation] = {}
    for i, src in enumerate(sources):
        chunk_id = src.get("chunk_id", f"unknown_{i}")
        metadata = src.get("metadata", {})
        citation_map[chunk_id] = Citation(
            source_id=chunk_id,
            doc_title=metadata.get("doc_title", metadata.get("source", f"document_{i}")),
            chunk_index=metadata.get("chunk_index", i),
            score=src.get("score", src.get("combined_score", 0.0)),
            strategy=metadata.get("strategy", "unknown"),
        )
    return citation_map


def build_references_section(citations: dict[str, Citation]) -> str:
    """Build a references section from citation map."""
    if not citations:
        return ""

    lines = ["## 参考资料\n"]
    for i, (chunk_id, c) in enumerate(citations.items(), 1):
        lines.append(
            f"{i}. **{c.doc_title}** (chunk {c.chunk_index}) "
            f"— 检索得分: {c.score:.2f}, 策略: {c.strategy}"
        )
    return "\n".join(lines)
