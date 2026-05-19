"""Tests for MCP web search integration."""

import pytest

from config.settings import settings
import research_agent.tools.web_search as ws_module
from research_agent.tools.web_search import search_web
from research_agent.tools.mcp_client import MCPClient


class TestWebSearchTool:
    """Tests for search_web without requiring actual MCP connection."""

    @pytest.mark.asyncio
    async def test_search_web_returns_empty_when_not_configured(self, monkeypatch):
        """search_web returns [] when TAVILY_API_KEY is empty."""
        monkeypatch.setattr(settings.mcp, "tavily_api_key", "")
        results = await search_web("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_web_returns_empty_when_mcp_fails(self, monkeypatch):
        """search_web returns [] when MCP call raises an exception."""
        monkeypatch.setattr(settings.mcp, "tavily_api_key", "fake-key")

        async def mock_call_tool(*args, **kwargs):
            raise RuntimeError("connection failed")

        monkeypatch.setattr(ws_module.mcp_client, "call_tool", mock_call_tool)
        results = await search_web("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_web_normalizes_results(self, monkeypatch):
        """search_web transforms Tavily results into agent format."""
        monkeypatch.setattr(settings.mcp, "tavily_api_key", "fake-key")

        tavily_response = '[{"title": "Test Page", "url": "https://example.com", "content": "Hello world", "score": 0.95}]'

        async def mock_call_tool(*args, **kwargs):
            return tavily_response

        monkeypatch.setattr(ws_module.mcp_client, "call_tool", mock_call_tool)
        results = await search_web("test query", max_results=5)

        assert len(results) == 1
        r = results[0]
        assert r["chunk_id"].startswith("web-")
        assert r["content"] == "Hello world"
        assert r["score"] == 0.95
        assert r["metadata"]["source"] == "web"
        assert r["metadata"]["url"] == "https://example.com"
        assert r["metadata"]["title"] == "Test Page"
        assert r["vector_score"] is None
        assert r["bm25_score"] is None


class TestMCPClient:
    """Tests for MCPClient lifecycle."""

    def test_client_starts_disconnected(self):
        client = MCPClient()
        assert client.is_connected is False
