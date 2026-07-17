"""Extract compact, source-backed context between research hops."""

from __future__ import annotations

from config.settings import settings


CONTEXT_SYSTEM_PROMPT = """你是研究证据整理器。请只根据给定检索片段提取可用于下一步检索的结构化上下文。

要求：
1. summary 是不超过 500 字的事实性摘要
2. entities 只列出片段中明确出现的实体或术语
3. facts 每条事实都必须能由 source_ids 中的来源支持
4. open_questions 列出当前资料无法确定、但可能需要下一跳回答的问题
5. 不要补充片段之外的知识，不要输出推理过程
6. summary、facts 和 open_questions 必须使用简体中文，专有名词可以保留英文
"""

SEARCH_QUERY_SYSTEM_PROMPT = """你是检索查询生成器。请结合当前问题与前序研究上下文，生成一条简短、独立、适合向量检索的查询。

要求：
1. 只保留回答当前问题必需的实体、术语和限定条件
2. 不要复制整段摘要，不要解释，不要添加来源列表
3. 查询必须能够脱离对话单独理解
4. 返回 JSON：{"query": "..."}
5. 用户问题为中文时，查询说明使用中文，专有名词和必要关键词可以保留英文
"""


async def extract_step_context(
    client,
    original_query: str,
    step_question: str,
    results: list[dict],
) -> dict:
    """Return a compact working-memory record grounded in retrieval results."""
    if not results:
        return {
            "summary": "没有检索到可用证据。",
            "entities": [],
            "facts": [],
            "open_questions": [step_question],
            "source_ids": [],
        }

    source_blocks = []
    source_ids = []
    for result in results[:5]:
        source_id = str(result.get("chunk_id", "unknown"))
        source_ids.append(source_id)
        source_blocks.append(
            f"[来源ID: {source_id}]\n{(result.get('content') or '')[:1000]}"
        )

    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "entities": {"type": "array", "items": {"type": "string"}},
            "facts": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "entities", "facts", "open_questions"],
    }
    messages = [
        {"role": "system", "content": CONTEXT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"原始问题：{original_query}\n"
                f"当前步骤：{step_question}\n\n"
                f"检索片段：\n{chr(10).join(source_blocks)}"
            ),
        },
    ]
    context = await client.chat_structured(messages, schema)
    max_chars = settings.reasoning.context_max_chars
    return {
        "summary": str(context.get("summary", ""))[:max_chars],
        "entities": [str(item)[:200] for item in context.get("entities", [])[:20]],
        "facts": [str(item)[:500] for item in context.get("facts", [])[:20]],
        "open_questions": [
            str(item)[:500] for item in context.get("open_questions", [])[:10]
        ],
        "source_ids": source_ids,
    }


def render_step_context(contexts: list[dict]) -> str:
    """Render only compact structured memory into the next search query."""
    blocks: list[str] = []
    for context in contexts:
        if context.get("low_confidence"):
            blocks.append("置信度提示：前序证据质量较低，下一跳需要重新验证。")
        if context.get("summary"):
            blocks.append(f"摘要：{context['summary']}")
        if context.get("entities"):
            blocks.append("实体/术语：" + "、".join(context["entities"][:12]))
        if context.get("facts"):
            blocks.append("已确认事实：" + "；".join(context["facts"][:8]))
    return "\n".join(blocks)[: settings.reasoning.context_max_chars]


async def build_contextual_search_query(
    client,
    question: str,
    contexts: list[dict],
) -> str:
    """Generate a bounded search query instead of embedding full working memory."""
    max_chars = settings.reasoning.search_query_max_chars
    rendered_context = render_step_context(contexts)
    if not rendered_context:
        return question.strip()[:max_chars]

    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    messages = [
        {"role": "system", "content": SEARCH_QUERY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"当前问题：{question}\n\n前序研究上下文：\n{rendered_context}",
        },
    ]
    try:
        result = await client.chat_structured(messages, schema, temperature=0.0)
        generated = " ".join(str(result.get("query", "")).split())
        if generated:
            return generated[:max_chars]
    except Exception:
        pass

    # Deterministic fallback keeps the current question and a small entity set.
    entities: list[str] = []
    for context in contexts:
        entities.extend(str(item) for item in context.get("entities", [])[:6])
    fallback = " ".join([question.strip(), *entities[:8]])
    return fallback[:max_chars]
