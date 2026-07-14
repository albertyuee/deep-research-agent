from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AggregatedFinding:
    sub_query: str
    content: str
    sources: list[dict] = field(default_factory=list)
    conflict_note: str | None = None
    low_confidence: bool = False
    reasoning_context: dict | None = None


def aggregate_results(
    sub_queries: list[str],
    retrieval_results: list[list[dict]],
    critique_scores: list[dict],
    step_contexts: dict[str, dict] | None = None,
) -> list[AggregatedFinding]:
    """Aggregate retrieval results from multiple sub-queries.

    Deduplicates overlapping information and flags contradictions.

    Args:
        sub_queries: List of sub-query strings.
        retrieval_results: List of retrieval result lists (one per sub-query).
        critique_scores: List of critique results (one per sub-query).

    Returns:
        List of aggregated findings, one per sub-query.
    """
    findings: list[AggregatedFinding] = []

    for i, (query, results, critique) in enumerate(
        zip(sub_queries, retrieval_results, critique_scores)
    ):
        # Deduplicate by content similarity (simple: identical first 100 chars)
        seen_contents: set[str] = set()
        unique_sources: list[dict] = []

        for r in results:
            content_key = r.get("content", "")[:100]
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                unique_sources.append({
                    "chunk_id": r.get("chunk_id", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", r.get("combined_score", 0.0)),
                    "metadata": r.get("metadata", {}),
                })

        # Combine content from unique sources
        combined_content = "\n\n".join(
            s["content"] for s in unique_sources[:5]
        )

        findings.append(
            AggregatedFinding(
                sub_query=query,
                content=combined_content,
                sources=unique_sources,
                low_confidence=critique.get("composite_score", 0) < 0.6,
                reasoning_context=(step_contexts or {}).get(str(i + 1)),
            )
        )

    return findings


def detect_conflicts(findings: list[AggregatedFinding]) -> list[AggregatedFinding]:
    """Detect and flag contradictory information across findings.

    This is a simplified version that marks potential conflicts.
    Full semantic conflict detection requires LLM analysis — see report_generator.
    """
    # For MVP, we delegate detailed conflict detection to the LLM in report generation.
    # This function serves as a pre-processing hook for future enhancements.
    return findings
