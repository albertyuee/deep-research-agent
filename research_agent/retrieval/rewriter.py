from __future__ import annotations

from enum import Enum


class RewriteAction(Enum):
    BROADEN = "broaden"
    NARROW = "narrow"
    REPHRASE = "rephrase"
    SWITCH_KEYWORDS = "switch_keywords"


REWRITE_PROMPTS = {
    RewriteAction.BROADEN: "以下查询的检索结果太少。请将查询改写得更宽泛，移除过于具体的限制条件，只返回改写后的查询：",
    RewriteAction.NARROW: "以下查询的检索结果太泛。请将查询改写得更具体，添加关键限定条件，只返回改写后的查询：",
    RewriteAction.REPHRASE: "以下查询检索效果不佳。请用不同的表达方式重新表述，保持原意不变，只返回改写后的查询：",
    RewriteAction.SWITCH_KEYWORDS: "以下查询的关键词匹配效果不佳。请提取核心关键词并重组成更简洁的查询，只返回改写后的查询：",
}


async def rewrite_query(
    client, original_query: str, action: RewriteAction, previous_results_summary: str = ""
) -> str:
    """Rewrite a query based on the specified action and previous failure context.

    Args:
        client: LLM client.
        original_query: The original query that needs rewriting.
        action: The type of rewrite to perform.
        previous_results_summary: Brief summary of why previous retrieval failed.

    Returns:
        Rewritten query string.
    """
    from research_agent.llm.base import BaseLLMClient

    system_msg = REWRITE_PROMPTS.get(action, REWRITE_PROMPTS[RewriteAction.REPHRASE])

    user_msg = f"原始查询：{original_query}"
    if previous_results_summary:
        user_msg += f"\n\n上次检索问题：{previous_results_summary}"

    messages = [
        {"role": "system", "content": f"{system_msg}\n只返回改写后的查询文本，不要解释。长度不超过 200 字。"},
        {"role": "user", "content": user_msg},
    ]
    result = await client.chat(messages, temperature=0.3)
    return result.strip()
