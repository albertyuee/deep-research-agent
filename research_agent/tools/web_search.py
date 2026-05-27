"""Web search tool — calls the MCP server and normalizes results.

Result format matches the agent's internal retrieval result format
so downstream nodes (critique, synthesis, citation) work without changes.
"""

from __future__ import annotations

import json
import uuid

from langsmith import traceable

from research_agent.tools.mcp_client import mcp_client
from config.settings import settings


@traceable(name="mcp_web_search", run_type="tool")
async def search_web(query: str, max_results: int | None = None) -> list[dict]:
    """Search the web via MCP and return agent-compatible result dicts.

    Args:
        query: The search query string.
        max_results: Max results, defaults to settings.mcp.tavily_max_results.

    Returns:
        List of result dicts matching the internal retrieval format:
        {chunk_id, content, score, vector_score, bm25_score, metadata}
        Returns empty list if web search is unavailable or fails.
    """
    if max_results is None:
        max_results = settings.mcp.tavily_max_results

    if not settings.mcp.tavily_api_key:
        return []

    try:
        raw = await mcp_client.call_tool("web_search", {
            "query": query,
            "max_results": max_results,
        })

        if not raw:
            return []

        web_results = json.loads(raw)

        if isinstance(web_results, dict) and "error" in web_results:
            return []

        normalized = []
        for r in web_results:
            normalized.append({
                "chunk_id": f"web-{uuid.uuid4().hex[:8]}",
                "content": r.get("content") or "",
                "score": r.get("score") or 0.0,
                "vector_score": None,
                "bm25_score": None,
                "metadata": {
                    "source": "web",
                    "source_type": "web",
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "strategy": "web_search",
                },
            })

        return normalized

    except Exception:
        return []
