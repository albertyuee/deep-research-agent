from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Citation:
    source_id: str
    doc_title: str = ""
    url: str = ""
    file_name: str = ""
    source_type: str = "local"  # "local" or "web"
    chunk_index: int = 0
    score: float = 0.0
    strategy: str = "unknown"


def format_citation(c: Citation) -> str:
    """Format a citation as inline markdown, with link for web sources."""
    label = c.doc_title or c.file_name or c.source_id
    if c.url:
        return f"[{label}]({c.url})"
    return f"[来源: {label}]"


def build_citation_map(sources: list[dict]) -> dict[str, Citation]:
    """Build a lookup map from chunk_id to Citation.

    Handles both local documents (file_name, source_path in metadata)
    and web search results (url, title in metadata).
    """
    citation_map: dict[str, Citation] = {}
    for i, src in enumerate(sources):
        chunk_id = src.get("chunk_id", f"unknown_{i}")
        metadata = src.get("metadata", {})

        source_type = metadata.get("source_type", "local")
        url = metadata.get("url", "")
        file_name = metadata.get("file_name", "")
        title = metadata.get("title", "")
        source_path = metadata.get("source_path", "")

        # Determine best display name
        doc_title = title or file_name or source_path or f"document_{i}"

        citation_map[chunk_id] = Citation(
            source_id=chunk_id,
            doc_title=doc_title,
            url=url,
            file_name=file_name or source_path,
            source_type=source_type,
            chunk_index=metadata.get("chunk_index", i),
            score=src.get("score", src.get("combined_score", 0.0)),
            strategy=metadata.get("strategy", "unknown"),
        )
    return citation_map


def build_references_section(citations: dict[str, Citation]) -> str:
    """Build a references section from citation map.

    Groups by source type — web results first (with clickable links),
    then local documents.
    """
    if not citations:
        return ""

    web_citations = [c for c in citations.values() if c.source_type == "web"]
    local_citations = [c for c in citations.values() if c.source_type != "web"]

    lines = ["## 参考资料\n"]

    # Web search sources
    if web_citations:
        lines.append("### 网络来源\n")
        seen_urls = set()
        idx = 1
        for c in web_citations:
            if c.url in seen_urls:
                continue
            seen_urls.add(c.url)
            label = c.doc_title or c.url
            lines.append(f"{idx}. [{label}]({c.url})")
            idx += 1

    # Local document sources
    if local_citations:
        if web_citations:
            lines.append("")
        lines.append("### 本地资料库\n")
        seen_files = set()
        idx = 1
        for c in local_citations:
            key = c.file_name or c.source_id
            if key in seen_files:
                continue
            seen_files.add(key)
            lines.append(
                f"{idx}. **{c.file_name or c.source_id}** "
                f"— 检索得分: {c.score:.2f}, 策略: {c.strategy}"
            )
            idx += 1

    return "\n".join(lines)
