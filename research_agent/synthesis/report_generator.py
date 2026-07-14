from __future__ import annotations

from research_agent.synthesis.aggregator import AggregatedFinding
from research_agent.synthesis.citation import Citation


REPORT_SYSTEM_PROMPT = """你是一个专业的研究报告撰写助手。基于检索到的资料，生成一份结构清晰、有据可查的研究报告。

报告要求：
1. 基于提供的资料回答，不要编造信息
2. 如果资料不充分或存在矛盾，明确指出
3. 为每个事实性陈述使用给定的 [来源: chunk_id] 格式标注出处
4. 只能引用输入中出现的 chunk_id，不要编造来源 ID
5. 使用 Markdown 格式
6. 不要生成"参考资料"或"参考文献"章节，系统会自动追加完整的来源列表

报告结构：
## 研究摘要
2-3 句话概述研究结论

## 详细发现
对每个子问题分别回答，引用具体来源

## 局限性说明
指出检索资料的不足或矛盾之处"""


def _build_context(
    original_query: str,
    findings: list[AggregatedFinding],
    citations: dict[str, Citation] | None,
) -> str:
    """Build source-labelled context so generated claims can be audited."""
    context_parts = [f"## 原始问题\n{original_query}\n"]

    for finding in findings:
        confidence_note = " ⚠️ 低置信度" if finding.low_confidence else ""
        source_blocks: list[str] = []
        for source in finding.sources[:5]:
            source_id = source.get("chunk_id", "unknown")
            citation = (citations or {}).get(source_id)
            label = citation.doc_title if citation else source_id
            if citation and citation.url:
                label = f"{label} | {citation.url}"
            source_blocks.append(
                f"[来源ID: {source_id} | 名称: {label}]\n{source.get('content', '')}"
            )

        evidence = "\n\n".join(source_blocks) or finding.content
        if finding.reasoning_context and finding.reasoning_context.get("summary"):
            evidence = (
                f"研究上下文摘要：{finding.reasoning_context['summary']}\n\n"
                + evidence
            )
        context_parts.append(
            f"### 子问题: {finding.sub_query}{confidence_note}\n{evidence}\n"
        )

    return "\n".join(context_parts)


async def generate_report(
    client,
    original_query: str,
    findings: list[AggregatedFinding],
    citations: dict[str, Citation] | None = None,
) -> str:
    """Generate a structured research report from aggregated findings.

    Args:
        client: LLM client.
        original_query: The original user query.
        findings: Aggregated findings from all sub-queries.
        citations: Optional citation map for reference.

    Returns:
        Markdown-formatted research report.
    """
    context = _build_context(original_query, findings, citations)

    messages = [
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": f"基于以下研究资料，生成研究报告：\n\n{context}"},
    ]

    return await client.chat(messages, temperature=0.3)


async def generate_report_streaming(
    client,
    original_query: str,
    findings: list[AggregatedFinding],
    citations: dict[str, Citation] | None = None,
):
    """Stream report generation chunks."""
    context = _build_context(original_query, findings, citations)

    messages = [
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": f"基于以下研究资料，生成研究报告：\n\n{context}"},
    ]

    async for chunk in client.stream_chat(messages, temperature=0.3):
        yield chunk
