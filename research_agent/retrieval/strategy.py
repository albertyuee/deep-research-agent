from __future__ import annotations

from typing import Literal

StrategyType = Literal["semantic", "keyword", "hybrid"]


_STRATEGY_PROMPT = """分析以下子问题，选择最合适的检索策略。

策略说明：
- "semantic"：语义向量检索 — 适合概念性、开放性、需要理解语义的问题
- "keyword"：BM25 关键词检索 — 适合包含特定实体名称、数字、术语、精确匹配的问题
- "hybrid"：混合检索（向量 + BM25 融合） — 适合两者都需要的情况

判断规则：
1. 如果问题包含具体的产品名、人名、地名、数字、专业术语 → "keyword" 或 "hybrid"
2. 如果问题是概念解释、趋势分析、观点类 → "semantic"
3. 如果不确定 → "hybrid"

只返回策略名称（semantic / keyword / hybrid），不要其他内容。"""


async def select_strategy(client, query: str) -> StrategyType:
    """Let the LLM agent autonomously select the retrieval strategy."""
    from research_agent.llm.base import BaseLLMClient

    messages = [
        {"role": "system", "content": _STRATEGY_PROMPT},
        {"role": "user", "content": query},
    ]
    response = await client.chat(messages, temperature=0.1)
    response = response.strip().lower()
    if response in ("semantic", "keyword", "hybrid"):
        return response  # type: ignore[return-value]
    return "hybrid"
