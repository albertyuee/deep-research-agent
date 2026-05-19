from __future__ import annotations

from typing import Literal

from research_agent.llm.base import BaseLLMClient
from config.settings import settings


def _build_system_prompt(enable_web_search: bool = False) -> str:
    """Build the decomposition prompt.

    enable_web_search: Whether web search is enabled by the user.
        Only when enabled AND API key is configured does the LLM see web as an option.
    """
    web_available = enable_web_search and bool(settings.mcp.tavily_api_key)

    web_instruction = (
        '- "web": 需要实时信息、最新数据或知识库没有覆盖的知识（联网搜索当前可用）\n'
        '- "both": 本地知识库和联网搜索都需要，互补使用'
        if web_available else
        '- "web": 当前不可用，请勿选择\n'
        '- "both": 当前不可用，请勿选择。如需联网信息，选择 "local"'
    )

    return f"""你是一个专业的研究规划助手。你的任务是将用户提出的复杂问题拆解为 2-5 个原子化的子问题。

拆解原则：
1. 每个子问题必须可以独立回答，不依赖其他子问题的结果
2. 子问题之间应覆盖原问题的所有方面，没有遗漏
3. 子问题按逻辑顺序排列（从基础到深入、从一般到具体）
4. 如果原问题很简单，返回 1 个子问题即可，不要强行拆解
5. 每个子问题必须标注推荐的检索策略和资料来源

检索策略（strategy）：
- "semantic"：语义向量检索，适合概念性、开放性、需要理解语义的问题
- "keyword"：BM25 关键词检索，适合包含特定实体名称、数字、术语、精确匹配的问题
- "hybrid"：混合检索（向量 + BM25），适合两者都需要的情况

资料来源（data_source）：
- "local"：本地知识库中应该有答案（已索引的文档）
{web_instruction}

返回格式（严格的 JSON）：
{{{{
  "sub_queries": [
    {{{{
      "index": 1,
      "question": "子问题文本",
      "strategy": "semantic",
      "data_source": "local",
      "rationale": "选择该策略和资料源的理由"
    }}}}
  ]
}}}}"""


async def decompose_query(
    client: BaseLLMClient,
    query: str,
    enable_web_search: bool = False,
) -> list[dict]:
    """Decompose a complex query into atomic sub-questions.

    Args:
        client: LLM client for decomposition.
        query: The original user query.
        enable_web_search: Whether web search is enabled by the user.

    Returns:
        List of sub-query dicts, each with index, question, strategy,
        data_source, and rationale.
    """
    messages = [
        {"role": "system", "content": _build_system_prompt(enable_web_search)},
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
                        "strategy": {
                            "type": "string",
                            "enum": ["semantic", "keyword", "hybrid"],
                        },
                        "data_source": {
                            "type": "string",
                            "enum": ["local", "web", "both"],
                        },
                        "rationale": {"type": "string"},
                    },
                    "required": ["index", "question", "strategy", "data_source", "rationale"],
                },
            }
        },
        "required": ["sub_queries"],
    }

    result = await client.chat_structured(messages, schema)
    return result.get("sub_queries", [])
