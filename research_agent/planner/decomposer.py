from __future__ import annotations

from typing import Literal

from research_agent.llm.base import BaseLLMClient
from config.settings import settings
from research_agent.state import ResearchMode


def _build_system_prompt(
    enable_web_search: bool = False,
    research_mode: ResearchMode = "auto",
    max_hops: int = 3,
) -> str:
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

    mode_instructions = {
        "auto": (
            "自动规划：可以独立回答的步骤使用 depends_on=[]；只有确实需要前序实体或事实时才建立依赖。"
        ),
        "parallel": (
            "并列研究：所有步骤必须互相独立，统一使用 hop=1、depends_on=[]、input_slots=[]。"
        ),
        "multihop": (
            "多跳推理：除第一步外，后续步骤应尽量依赖前序步骤的实体或事实；"
            "至少生成一条依赖关系，并确保 hop 不超过最大跳数。"
        ),
    }
    mode_instruction = mode_instructions[research_mode]

    max_sub_queries = settings.reasoning.max_sub_queries

    return f"""你是一个专业的研究规划助手。你的任务是将用户提出的复杂问题拆解为 1-{max_sub_queries} 个研究步骤。

拆解原则：
1. 当前研究模式：{research_mode}。{mode_instruction}
2. 子问题之间应覆盖原问题的所有方面，没有遗漏
3. 子问题按逻辑顺序排列（从基础到深入、从一般到具体）
4. 如果原问题很简单，返回 1 个子问题即可，不要强行拆解
5. 每个步骤必须标注推荐的检索策略、资料来源和 hop
6. 多跳步骤的 question 可以使用前序步骤产出的实体/事实，input_slots 写明需要哪些信息
7. 最大允许跳数为 {max_hops}
8. question 和 rationale 必须使用简体中文；框架名、产品名等专有名词可以保留英文
9. 即使用户问题或参考资料包含英文，也要用中文描述研究步骤和规划理由

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
      "rationale": "选择该策略和资料源的理由",
      "hop": 1,
      "depends_on": [],
      "input_slots": [],
      "terminal": false
    }}}},
    {{{{
      "index": 2,
      "question": "基于第 1 步得到的实体，继续回答……",
      "strategy": "hybrid",
      "data_source": "local",
      "rationale": "需要使用前一步实体",
      "hop": 2,
      "depends_on": [1],
      "input_slots": ["entities", "facts"],
      "terminal": true
    }}}}
  ]
}}}}"""


async def decompose_query(
    client: BaseLLMClient,
    query: str,
    enable_web_search: bool = False,
    research_mode: ResearchMode = "auto",
    max_hops: int = 3,
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
        {
            "role": "system",
            "content": _build_system_prompt(
                enable_web_search,
                research_mode,
                max_hops,
            ),
        },
        {"role": "user", "content": f"请拆解以下问题：\n{query}"},
    ]

    schema = {
        "type": "object",
        "properties": {
            "sub_queries": {
                "type": "array",
                "maxItems": settings.reasoning.max_sub_queries,
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
                        "hop": {"type": "integer", "minimum": 1},
                        "depends_on": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 1},
                        },
                        "input_slots": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "terminal": {"type": "boolean"},
                    },
                    "required": ["index", "question", "strategy", "data_source", "rationale"],
                },
            }
        },
        "required": ["sub_queries"],
    }

    result = await client.chat_structured(messages, schema)
    return result.get("sub_queries", [])
