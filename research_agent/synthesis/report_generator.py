from __future__ import annotations

from research_agent.synthesis.aggregator import AggregatedFinding
from research_agent.synthesis.citation import Citation, format_citation, build_citation_map


REPORT_SYSTEM_PROMPT = """你是一个专业的研究报告撰写助手。基于检索到的资料，生成一份结构清晰、有据可查的研究报告。

报告要求：
1. 基于提供的资料回答，不要编造信息
2. 如果资料不充分或存在矛盾，明确指出
3. 为每个事实性陈述标注引用来源
4. 使用 Markdown 格式

报告结构：
## 研究摘要
2-3 句话概述研究结论

## 详细发现
对每个子问题分别回答，引用具体来源

## 局限性说明
指出检索资料的不足或矛盾之处

## 参考资料
列出所有引用的来源"""


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
    # Build context from findings
    context_parts = [f"## 原始问题\n{original_query}\n"]

    for f in findings:
        source_markers = ""
        if f.sources:
            source_ids = ", ".join(s.get("chunk_id", "?") for s in f.sources[:3])
            source_markers = f"\n可用来源: {source_ids}"

        confidence_note = " ⚠️ 低置信度" if f.low_confidence else ""
        context_parts.append(
            f"### 子问题: {f.sub_query}{confidence_note}\n{f.content}{source_markers}\n"
        )

    context = "\n".join(context_parts)

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
    context_parts = [f"## 原始问题\n{original_query}\n"]

    for f in findings:
        confidence_note = " ⚠️ 低置信度" if f.low_confidence else ""
        context_parts.append(
            f"### 子问题: {f.sub_query}{confidence_note}\n{f.content}\n"
        )

    context = "\n".join(context_parts)

    messages = [
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": f"基于以下研究资料，生成研究报告：\n\n{context}"},
    ]

    async for chunk in client.stream_chat(messages, temperature=0.3):
        yield chunk
