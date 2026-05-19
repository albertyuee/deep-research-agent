"""MCP Server for web search via Tavily API.

Runs as a stdio subprocess, communicates with the agent via MCP protocol.
"""

import json
import os
import sys

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = "https://api.tavily.com/search"

server = Server("web-search")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="web_search",
            description=(
                "搜索互联网获取实时信息。当需要当前数据、近期事件或本地知识库未覆盖的"
                "知识时使用此工具。返回网页标题、URL 和内容摘要。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回结果的最大数量，默认 5",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name != "web_search":
        raise ValueError(f"Unknown tool: {name}")

    query = arguments["query"]
    max_results = arguments.get("max_results", 5)

    if not TAVILY_API_KEY:
        return [TextContent(
            type="text",
            text=json.dumps({"error": "TAVILY_API_KEY not configured", "results": []})
        )]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TAVILY_API_URL,
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])
    formatted = json.dumps(results, ensure_ascii=False)
    return [TextContent(type="text", text=formatted)]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
