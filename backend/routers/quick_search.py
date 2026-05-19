"""Quick Search API — fast retrieval + LLM summarization without the full agent pipeline."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.research_service import task_manager
from research_agent.llm.factory import create_llm_client
from research_agent.retrieval.vector_store import create_vector_store
from research_agent.retrieval.bm25 import BM25Retriever
from research_agent.retrieval.hybrid import HybridRetriever
from config.settings import settings

router = APIRouter(prefix="/quick-search", tags=["quick-search"])

_SUMMARY_SYSTEM_PROMPT = """你是一个研究助手。基于以下检索到的文档片段，用中文简洁地回答用户的问题。

要求：
- 回答要准确、简洁，控制在 300 字以内
- 优先使用检索结果中的信息
- 如果检索结果不足以回答问题，如实告知用户
- 使用 Markdown 格式组织回答，包括要点列表"""

_vector_store = None
_bm25: BM25Retriever | None = None


def _get_hybrid() -> HybridRetriever:
    global _vector_store, _bm25
    if _vector_store is None:
        _vector_store = create_vector_store()
    if _bm25 is None:
        _bm25 = BM25Retriever()
    return HybridRetriever(_vector_store, _bm25)


class QuickSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class QuickSearchResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


@router.post("", response_model=QuickSearchResponse)
async def quick_search(req: QuickSearchRequest):
    """Execute a fast hybrid search + LLM summarization."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    t0 = time.time()

    try:
        hybrid = _get_hybrid()
        results = hybrid.search(req.query, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {e}")

    sources = [
        {
            "chunk_id": r.chunk_id,
            "content": r.content,
            "score": r.combined_score,
            "metadata": r.metadata,
        }
        for r in results
    ]

    try:
        client = create_llm_client()
        context = "\n\n---\n\n".join(
            f"[来源 {i+1}] {r.content[:800]}"
            for i, r in enumerate(results[:5])
        )
        messages = [
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": f"检索结果：\n\n{context}\n\n用户问题：{req.query}\n\n请回答："},
        ]
        raw = await client.chat(messages, temperature=0.3, max_tokens=1024)
        summary = raw.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 摘要生成失败: {e}")

    elapsed_ms = int((time.time() - t0) * 1000)

    return QuickSearchResponse(
        success=True,
        data={
            "query": req.query,
            "summary": summary,
            "sources": sources,
            "elapsed_ms": elapsed_ms,
        },
    )
