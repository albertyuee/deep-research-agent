"""Tests for source-labelled report context."""

import pytest

from research_agent.synthesis.aggregator import AggregatedFinding
from research_agent.synthesis.citation import build_citation_map
from research_agent.synthesis.report_generator import generate_report_streaming


class CapturingClient:
    def __init__(self):
        self.messages = None

    async def stream_chat(self, messages, **kwargs):
        self.messages = messages
        yield "报告"


@pytest.mark.asyncio
async def test_streaming_report_includes_allowed_source_ids():
    client = CapturingClient()
    findings = [
        AggregatedFinding(
            sub_query="Transformer 用在哪里？",
            content="fallback content",
            sources=[
                {
                    "chunk_id": "chunk-1",
                    "content": "Transformer 用于医疗影像分析。",
                    "metadata": {"file_name": "medical.md"},
                }
            ],
        )
    ]
    citations = build_citation_map(findings[0].sources)

    chunks = [
        chunk
        async for chunk in generate_report_streaming(
            client, "问题", findings, citations
        )
    ]

    user_prompt = client.messages[-1]["content"]
    assert chunks == ["报告"]
    assert "来源ID: chunk-1" in user_prompt
    assert "只能引用输入中出现的 chunk_id" in client.messages[0]["content"]
