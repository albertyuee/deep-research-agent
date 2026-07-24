"""Quick Search API — fast retrieval + LLM summarization without the full agent pipeline."""

from __future__ import annotations

import logging
import time
import traceback
from typing import Literal

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.services.research_service import task_manager
from research_agent.llm.factory import create_llm_client
from research_agent.retrieval.hybrid import HybridRetriever
from research_agent.retrieval.service import retrieval_service
from config.settings import settings
from backend.auth import User, allowed_upload_ids, current_user
from backend.routers.documents import _read_files_meta

# Use Uvicorn's configured logger so retrieval diagnostics are written to the
# same backend log as request and timing records in production startup.
logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/quick-search", tags=["quick-search"])

_SUMMARY_SYSTEM_PROMPT = """你是一个研究助手。基于对话上下文和检索到的文档片段，用中文简洁地回答用户的问题。

要求：
- 回答要准确、简洁，控制在 300 字以内
- 优先使用检索结果中的信息
- 用户的问题如果依赖上文，要结合最近对话理解指代
- 如果检索结果不足以回答问题，如实告知用户
- 使用 Markdown 格式组织回答，包括要点列表"""

_REWRITE_SYSTEM_PROMPT = """你负责把用户当前问题改写成适合知识库检索的独立问题。

要求：
- 如果当前问题包含“它、这个、刚才、继续、展开”等依赖上文的指代，请结合最近对话补全指代
- 如果当前问题本身已经完整，直接原样返回
- 只返回改写后的问题，不要解释"""

def _get_hybrid() -> HybridRetriever:
    return retrieval_service.get_hybrid()


class QuickSearchHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class QuickSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    history: list[QuickSearchHistoryMessage] = Field(default_factory=list, max_length=20)


class QuickSearchResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


def _history_to_messages(history: list[QuickSearchHistoryMessage]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for item in history[-8:]:
        content = item.content.strip()
        if content:
            messages.append({"role": item.role, "content": content[:1500]})
    return messages


async def _rewrite_search_query(client, query: str, history_messages: list[dict[str, str]]) -> str:
    if not history_messages:
        return query.strip()

    messages = [
        {"role": "system", "content": _REWRITE_SYSTEM_PROMPT},
        *history_messages,
        {"role": "user", "content": query.strip()},
    ]
    rewritten = (await client.chat(messages, temperature=0.0, max_tokens=256)).strip()
    return rewritten[:1000] or query.strip()


@router.post("", response_model=QuickSearchResponse)
async def quick_search(req: QuickSearchRequest, user: User = Depends(current_user)):
    """Execute a fast hybrid search + LLM summarization."""
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    t0 = time.time()
    history_messages = _history_to_messages(req.history)
    client = None
    search_query = query

    if history_messages:
        try:
            client = create_llm_client()
            search_query = await _rewrite_search_query(client, query, history_messages)
        except Exception:
            logger.warning(f"Query rewrite failed, using original query: {query}", exc_info=True)
            search_query = query

    try:
        hybrid = _get_hybrid()
        files = _read_files_meta().get("files", [])
        access_ids = allowed_upload_ids(user, files)
        results = hybrid.search(search_query, top_k=req.top_k, allowed_upload_ids=access_ids)
    except Exception as e:
        tb = traceback.format_exc()
        logger.exception(f"检索失败: {e}")
        raise HTTPException(status_code=500, detail=f"检索失败: {type(e).__name__}: {e}\n{tb}")

    logger.info(
        "Quick search retrieval query=%r rewritten=%r top_k=%s returned=%s sources=%s",
        query,
        search_query if search_query != query else None,
        req.top_k,
        len(results),
        [
            {
                "chunk_id": result.chunk_id,
                "file_name": result.metadata.get("file_name") or result.metadata.get("source"),
                "vector_score": round(result.vector_score, 4),
                "bm25_score": round(result.bm25_score, 4),
                "combined_score": round(result.combined_score, 4),
                "rerank_score": (
                    round(result.rerank_score, 4)
                    if result.rerank_score is not None
                    else None
                ),
            }
            for result in results[:5]
        ],
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Quick search retrieval previews=%s",
            [result.content[:100].replace("\n", " ") for result in results[:5]],
        )

    sources = [
        {
            "chunk_id": r.chunk_id,
            "content": r.content,
            "score": r.combined_score,
            "rerank_score": r.rerank_score,
            "metadata": r.metadata,
        }
        for r in results
    ]

    try:
        if client is None:
            client = create_llm_client()
        context = "\n\n---\n\n".join(
            f"[来源 {i+1}] {r.content[:800]}"
            for i, r in enumerate(results[:5])
        )
        messages = [
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            *history_messages,
            {
                "role": "user",
                "content": (
                    f"检索问题：{search_query}\n\n"
                    f"检索结果：\n\n{context}\n\n"
                    f"用户当前问题：{query}\n\n"
                    "请结合对话上下文和检索结果回答："
                ),
            },
        ]
        raw = await client.chat(messages, temperature=0.3, max_tokens=1024)
        summary = raw.strip()
    except Exception as e:
        tb = traceback.format_exc()
        logger.exception(f"LLM 摘要生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"LLM 摘要生成失败: {type(e).__name__}: {e}\n{tb}")

    elapsed_ms = int((time.time() - t0) * 1000)

    return QuickSearchResponse(
        success=True,
        data={
            "query": query,
            "rewritten_query": search_query if search_query != query else None,
            "summary": summary,
            "sources": sources,
            "elapsed_ms": elapsed_ms,
        },
    )
