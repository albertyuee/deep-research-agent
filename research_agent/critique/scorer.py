from __future__ import annotations

from dataclasses import dataclass, field
import re

from config.settings import settings


@dataclass
class CritiqueResult:
    composite_score: float
    relevance_score: float
    completeness_score: float
    passed: bool
    retry_suggestion: str | None = None
    reasoning: str = ""


CRITIQUE_SYSTEM_PROMPT = """你是一个检索质量评估专家。评估检索结果在回答给定问题时的质量。

评估两个维度：
1. **相关性** (relevance, 0-1)：检索内容与问题的语义匹配程度
2. **完整性** (completeness, 0-1)：检索内容是否覆盖了回答该问题所需的关键信息点

综合评分 = 0.6 × 相关性 + 0.4 × 完整性

评分标准：
- 0.8-1.0：优秀，内容高度相关且完整
- 0.6-0.8：良好，基本可用但有小缺陷
- 0.4-0.6：一般，相关性或完整性不足
- 0.0-0.4：差，基本不可用

如果评分 < 0.6，给出具体的检索改进建议（如"扩大检索范围"、"增加关键词 X"、"切换为混合检索"等）。

语言要求（必须遵守）：
- reasoning 和 retry_suggestion 必须使用简体中文
- 即使问题、技术名词或检索资料是英文，也必须用中文解释评价结论
- 产品名、框架名和必要的检索关键词可以保留英文，但禁止输出完整的英文说明句

返回 JSON 格式。"""


def _contains_chinese(text: str | None) -> bool:
    return bool(text and re.search(r"[\u4e00-\u9fff]", text))


def _chinese_reasoning_fallback(relevance: float, completeness: float) -> str:
    """Guarantee a Chinese UI message if a provider ignores language rules."""
    if relevance < 0.4 and completeness < 0.4:
        return "检索内容与问题的核心主题相关性较低，也没有覆盖回答所需的关键信息。"
    if relevance < completeness:
        return "检索内容覆盖了部分信息，但与问题核心主题的相关性不足。"
    if completeness < relevance:
        return "检索内容与问题具有一定相关性，但关键信息覆盖不完整。"
    return "检索内容与问题基本相关，信息覆盖程度与当前评分一致。"


async def critique_retrieval(
    client, query: str, retrieved_texts: list[str], threshold: float | None = None
) -> CritiqueResult:
    """Evaluate the quality of retrieved results for a given query.

    Args:
        client: LLM client.
        query: The search query.
        retrieved_texts: Retrieved document chunks to evaluate.
        threshold: Pass/fail threshold (default from settings).

    Returns:
        CritiqueResult with scores and pass/fail decision.
    """
    threshold = threshold or settings.retrieval.critique_threshold

    if not retrieved_texts:
        return CritiqueResult(
            composite_score=0.0,
            relevance_score=0.0,
            completeness_score=0.0,
            passed=False,
            retry_suggestion="检索无结果，建议扩大检索范围或使用更通用的查询词",
            reasoning="没有检索到可用于回答该问题的内容。",
        )

    # Build context from retrieved texts
    texts_block = "\n---\n".join(
        f"[{i+1}] {t[:500]}" for i, t in enumerate(retrieved_texts[:5])
    )

    messages = [
        {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"问题：{query}\n\n检索到的内容：\n{texts_block}",
        },
    ]

    schema = {
        "type": "object",
        "properties": {
            "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
            "completeness_score": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {
                "type": "string",
                "description": "使用简体中文说明评分理由",
            },
            "retry_suggestion": {
                "type": "string",
                "description": "使用简体中文给出检索改进建议",
            },
        },
        "required": ["relevance_score", "completeness_score"],
    }

    result = await client.chat_structured(messages, schema)
    relevance = result.get("relevance_score", 0.5)
    completeness = result.get("completeness_score", 0.5)
    composite = 0.6 * relevance + 0.4 * completeness

    reasoning = str(result.get("reasoning", "")).strip()
    retry_suggestion = str(result.get("retry_suggestion", "")).strip()
    if not _contains_chinese(reasoning):
        reasoning = _chinese_reasoning_fallback(relevance, completeness)
    if composite < threshold and not _contains_chinese(retry_suggestion):
        retry_suggestion = "建议补充与问题核心主题直接相关的中英文关键词，扩大检索范围，并尝试混合检索。"

    return CritiqueResult(
        composite_score=round(composite, 2),
        relevance_score=round(relevance, 2),
        completeness_score=round(completeness, 2),
        passed=composite >= threshold,
        retry_suggestion=retry_suggestion if composite < threshold else None,
        reasoning=reasoning,
    )
