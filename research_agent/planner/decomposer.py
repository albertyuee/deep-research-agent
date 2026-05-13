from __future__ import annotations

import json
from typing import Literal

from research_agent.llm.base import BaseLLMClient


DECOMPOSITION_SYSTEM_PROMPT = """你是一个专业的研究规划助手。你的任务是将用户提出的复杂问题拆解为 2-5 个原子化的子问题。

拆解原则：
1. 每个子问题必须可以独立回答，不依赖其他子问题的结果
2. 子问题之间应覆盖原问题的所有方面，没有遗漏
3. 子问题按逻辑顺序排列（从基础到深入、从一般到具体）
4. 如果原问题很简单，返回 1 个子问题即可，不要强行拆解
5. 每个子问题必须标注推荐的检索策略："semantic"（语义检索，适合概念性问题）、"keyword"（关键词检索，适合实体/术语/数字查询）、"hybrid"（混合检索）

返回格式（严格的 JSON）：
{
  "sub_queries": [
    {
      "index": 1,
      "question": "子问题文本",
      "strategy": "semantic",
      "rationale": "选择该策略的理由"
    }
  ]
}"""


async def decompose_query(client: BaseLLMClient, query: str) -> list[dict]:
    """Decompose a complex query into atomic sub-questions.

    Args:
        client: LLM client for decomposition.
        query: The original user query.

    Returns:
        List of sub-query dicts, each with index, question, strategy, rationale.
    """
    messages = [
        {"role": "system", "content": DECOMPOSITION_SYSTEM_PROMPT},
        {"role": "user", "content": f"请拆解以下问题：\n{query}"},
    ]

    schema = {
        "type": "object",
        "properties": {
            "sub_queries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "question": {"type": "string"},
                        "strategy": {"type": "string", "enum": ["semantic", "keyword", "hybrid"]},
                        "rationale": {"type": "string"},
                    },
                    "required": ["index", "question", "strategy", "rationale"],
                },
            }
        },
        "required": ["sub_queries"],
    }

    result = await client.chat_structured(messages, schema)
    return result.get("sub_queries", [])
