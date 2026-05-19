# MCP Web Search Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Deep Research Agent 接入 MCP Web Search，Agent 自主判断子问题是否需要联网搜索，将外部搜索结果与本地检索结果融合，保持引用溯源能力。

**Architecture:** 自建 MCP Server（Python）封装 Tavily Search API，通过 stdio 传输与 Agent 进程通信。Agent 端的 MCP Client 管理连接生命周期。分解节点新增 `data_source` 字段（local/web/both），检索节点根据该字段分发到本地检索或 MCP 工具调用。Web 结果与本地结果用统一格式表示，下游 Critique/Synthesis/Citation 模块无需修改。

**Tech Stack:** mcp 1.27.0 (已安装), httpx 0.28.1 (已安装), Tavily Search API (免费额度 1000 次/月)

**设计原则:**
- Web search 不可用时 Agent 自动降级为纯本地检索，不报错
- 复用现有 SSE 事件机制，新增 `web_search_start` / `web_search_result` 事件
- 检索结果统一格式，`metadata.source` 区分 `"local"` / `"web"`，引用模块自动适配
- MCP Server 进程 = 单例，App 启动时拉起，关闭时终止

---

### Task 1: 添加 MCP 配置

**Files:**
- Modify: `config/settings.py:88-112`
- Modify: `config/.env.example`
- Modify: `pyproject.toml:1-31`

- [ ] **Step 1: 在 settings.py 中添加 MCPSettings 类**

```python
# 在 RetrievalSettings 之后、Settings 之前插入

class MCPSettings(BaseSettings):
    model_config = {
        "env_prefix": "MCP_",
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    web_search_enabled: bool = False
    tavily_api_key: str = ""
    tavily_max_results: int = 5
    web_search_timeout: float = 30.0


class Settings(BaseSettings):
    model_config = {
        "env_file": Path(__file__).parent / ".env",
        "extra": "ignore"
    }

    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)  # ← 新增

    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")
```

- [ ] **Step 2: 验证 settings 能正确加载**

```bash
python3 -c "
from config.settings import settings
print('MCP enabled:', settings.mcp.web_search_enabled)
print('Tavily key:', 'SET' if settings.mcp.tavily_api_key else 'NOT SET')
"
```

Expected: `MCP enabled: False` / `Tavily key: NOT SET`

- [ ] **Step 3: 更新 .env.example 添加 MCP 配置项**

在 `config/.env.example` 末尾追加：

```env
# ────────── MCP Web Search ──────────
# 启用 Web Search：在 Tavily 注册获取 API Key (https://tavily.com)
# 免费额度 1000 次/月，足以进行开发和演示
MCP_WEB_SEARCH_ENABLED=false
MCP_TAVILY_API_KEY=
MCP_TAVILY_MAX_RESULTS=5
```

- [ ] **Step 4: 更新 pyproject.toml 确认依赖**

`mcp` 和 `httpx` 均已安装在当前环境（mcp==1.27.0, httpx==0.28.1）。不需要修改 pyproject.toml，但验证：

```bash
python3 -c "import mcp; print('mcp', mcp.__version__)"
python3 -c "import httpx; print('httpx', httpx.__version__)"
```

Expected: `mcp 1.27.0` / `httpx 0.28.1`

- [ ] **Step 5: Commit**

```bash
git add config/settings.py config/.env.example
git commit -m "feat: add MCP configuration for web search integration"
```

---

### Task 2: 创建 MCP Web Search Server

**Files:**
- Create: `mcp_servers/__init__.py`
- Create: `mcp_servers/web_search/__init__.py`
- Create: `mcp_servers/web_search/server.py`
- Create: `mcp_servers/web_search/__main__.py`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p mcp_servers/web_search
```

- [ ] **Step 2: 创建 `mcp_servers/__init__.py`**

```python
# mcp_servers/__init__.py
```

- [ ] **Step 3: 创建 `mcp_servers/web_search/__init__.py`**

```python
# mcp_servers/web_search/__init__.py
```

- [ ] **Step 4: 创建 MCP Server 实现 `mcp_servers/web_search/server.py`**

```python
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
```

- [ ] **Step 5: 创建入口点 `mcp_servers/web_search/__main__.py`**

```python
"""Entry point: python -m mcp_servers.web_search"""

from mcp_servers.web_search.server import main
import asyncio

asyncio.run(main())
```

- [ ] **Step 6: 验证 MCP Server 能独立启动**

```bash
TAVILY_API_KEY=test python3 -m mcp_servers.web_search &
PID=$!
sleep 2 && kill $PID 2>/dev/null
echo "Server started and stopped OK"
```

Expected: 进程正常启动和退出（因为是 stdio 通信，看不到输出是正常的）

- [ ] **Step 7: Commit**

```bash
git add mcp_servers/
git commit -m "feat: add MCP web search server wrapping Tavily API"
```

---

### Task 3: 创建 MCP Client 连接管理器

**Files:**
- Create: `research_agent/tools/__init__.py`
- Create: `research_agent/tools/mcp_client.py`

- [ ] **Step 1: 创建 `research_agent/tools/__init__.py`**

```python
# research_agent/tools/__init__.py

from research_agent.tools.mcp_client import mcp_client
from research_agent.tools.web_search import search_web

__all__ = ["mcp_client", "search_web"]
```

- [ ] **Step 2: 创建 MCP Client `research_agent/tools/mcp_client.py`**

```python
"""MCP client connection manager.

Manages the lifecycle of MCP server subprocess connections.
Provides a singleton client for tool calls across the agent.
"""

from __future__ import annotations

import sys
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from config.settings import settings


class MCPClient:
    """Long-lived MCP client that connects to the web search server via stdio.

    Lifecycle:
        connect()    — start server subprocess, initialize session
        call_tool()  — invoke a tool on the server
        disconnect() — clean shutdown of session and subprocess
    """

    def __init__(self):
        self._session: ClientSession | None = None
        self._read = None
        self._write = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Start the MCP server subprocess and initialize the session."""
        if self._connected:
            return

        if not settings.mcp.tavily_api_key:
            print("[MCP] TAVILY_API_KEY not set, skipping MCP connection",
                  flush=True, file=sys.stderr)
            return

        try:
            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "mcp_servers.web_search"],
                env={
                    **__import__("os").environ,
                    "TAVILY_API_KEY": settings.mcp.tavily_api_key,
                },
            )

            # Enter stdio_client context manager
            self._stdio_ctx = stdio_client(server_params)
            self._read, self._write = await self._stdio_ctx.__aenter__()

            # Enter ClientSession context manager
            self._session_ctx = ClientSession(self._read, self._write)
            self._session = await self._session_ctx.__aenter__()

            await self._session.initialize()
            self._connected = True

            # Log available tools
            tools_result = await self._session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print(f"[MCP] Connected. Available tools: {tool_names}",
                  flush=True, file=sys.stderr)

        except Exception as e:
            print(f"[MCP] Failed to connect: {e}", flush=True, file=sys.stderr)
            self._connected = False

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call an MCP tool and return its text output.

        Returns empty string if client is not connected or call fails.
        """
        if not self._connected or not self._session:
            return ""

        try:
            result = await self._session.call_tool(name, arguments)

            # Extract text from the first TextContent block
            for block in result.content:
                if hasattr(block, "text"):
                    return block.text

            return ""

        except Exception as e:
            print(f"[MCP] call_tool '{name}' failed: {e}",
                  flush=True, file=sys.stderr)
            return ""

    async def disconnect(self) -> None:
        """Shut down the MCP session and server subprocess."""
        if not self._connected:
            return

        try:
            if hasattr(self, "_session_ctx"):
                await self._session_ctx.__aexit__(None, None, None)
            if hasattr(self, "_stdio_ctx"):
                await self._stdio_ctx.__aexit__(None, None, None)
        except Exception as e:
            print(f"[MCP] Error during disconnect: {e}",
                  flush=True, file=sys.stderr)
        finally:
            self._session = None
            self._connected = False
            print("[MCP] Disconnected", flush=True, file=sys.stderr)


# Global singleton
mcp_client = MCPClient()
```

- [ ] **Step 3: 验证导入正确**

```bash
python3 -c "from research_agent.tools.mcp_client import mcp_client; print('MCPClient imported OK, connected:', mcp_client.is_connected)"
```

Expected: `MCPClient imported OK, connected: False`

- [ ] **Step 4: Commit**

```bash
git add research_agent/tools/
git commit -m "feat: add MCP client connection manager for web search"
```

---

### Task 4: 创建 WebSearchTool 封装

**Files:**
- Create: `research_agent/tools/web_search.py`

- [ ] **Step 1: 创建 `research_agent/tools/web_search.py`**

```python
"""Web search tool — calls the MCP server and normalizes results.

Result format matches the agent's internal retrieval result format
so downstream nodes (critique, synthesis, citation) work without changes.
"""

from __future__ import annotations

import json
import uuid

from research_agent.tools.mcp_client import mcp_client
from config.settings import settings


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
                "content": r.get("content", ""),
                "score": r.get("score", 0.8),
                "vector_score": None,
                "bm25_score": None,
                "metadata": {
                    "source": "web",
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "strategy": "web_search",
                },
            })

        return normalized

    except Exception:
        return []
```

- [ ] **Step 2: 验证模块导入**

```bash
python3 -c "from research_agent.tools.web_search import search_web; print('search_web imported OK')"
```

Expected: `search_web imported OK`

- [ ] **Step 3: Commit**

```bash
git add research_agent/tools/web_search.py research_agent/tools/__init__.py
git commit -m "feat: add web search tool with normalized result format"
```

---

### Task 5: 修改分解器 — 让 Agent 判断是否需要联网搜索

**Files:**
- Modify: `research_agent/planner/decomposer.py`

- [ ] **Step 1: 更新分解 Prompt 和 Schema**

```python
# research_agent/planner/decomposer.py — 替换整个文件

from __future__ import annotations

from typing import Literal

from research_agent.llm.base import BaseLLMClient
from config.settings import settings


def _build_system_prompt() -> str:
    """Build the decomposition prompt, dynamically informing about web search availability."""
    web_available = bool(settings.mcp.tavily_api_key)

    web_instruction = (
        '- "web": 需要实时信息、最新数据或知识库没有覆盖的知识（联网搜索当前可用）'
        if web_available else
        '- "web": 当前不可用，请勿选择。如需联网信息，选择 "local"，我会从已有知识库中尽力查找'
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
- "both"：本地知识库和联网搜索都需要，互补使用

返回格式（严格的 JSON）：
{{
  "sub_queries": [
    {{
      "index": 1,
      "question": "子问题文本",
      "strategy": "semantic",
      "data_source": "local",
      "rationale": "选择该策略和资料源的理由"
    }}
  ]
}}"""


async def decompose_query(client: BaseLLMClient, query: str) -> list[dict]:
    """Decompose a complex query into atomic sub-questions.

    Args:
        client: LLM client for decomposition.
        query: The original user query.

    Returns:
        List of sub-query dicts, each with index, question, strategy,
        data_source, and rationale.
    """
    messages = [
        {"role": "system", "content": _build_system_prompt()},
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
```

- [ ] **Step 2: 验证分解器正常工作**

```bash
python3 -c "
import asyncio
from research_agent.llm.factory import create_llm_client
from research_agent.planner.decomposer import decompose_query

async def test():
    client = create_llm_client()
    result = await decompose_query(client, '最近AI领域有哪些重要进展？')
    for sq in result:
        print(f\"  [{sq['index']}] {sq['question'][:40]}... source={sq['data_source']} strategy={sq['strategy']}\")

asyncio.run(test())
"
```

Expected: 能看到每个子问题的 `data_source` 字段（由于没配 Tavily key，应都是 `"local"`）

- [ ] **Step 3: Commit**

```bash
git add research_agent/planner/decomposer.py
git commit -m "feat: add data_source field to decomposition for web search routing"
```

---

### Task 6: 修改检索节点 — 集成 Web Search

**Files:**
- Modify: `research_agent/graph.py:95-181`

- [ ] **Step 1: 修改 `retrieval_node` 函数**

`research_agent/graph.py:95-181` 替换为以下内容：

```python
async def retrieval_node(state: ResearchState) -> ResearchState:
    """Execute retrieval for the current sub-query.

    Dispatches to local retrieval (Chroma/BM25) and/or web search (MCP)
    based on the data_source field in the sub-query.
    """
    task_id = state.get("task_id", "")
    step_idx = state["current_step"]
    sub_queries = state["sub_queries"]
    retry_count = state.get("retry_count", 0)

    if step_idx >= len(sub_queries):
        return state

    sub_q = sub_queries[step_idx]
    query = sub_q["question"]
    data_source = sub_q.get("data_source", "local")

    # Determine retrieval strategy — on retry, may switch strategy
    client = create_llm_client()
    if retry_count == 0:
        strategy = sub_q.get("strategy", "hybrid")
    elif retry_count == 2:
        original = sub_q.get("strategy", "hybrid")
        strategy = "keyword" if original == "semantic" else "semantic"
    else:
        strategy = await select_strategy(client, query)

    # On retry, rewrite the query
    if retry_count > 0:
        action_map = {
            1: RewriteAction.BROADEN,
            2: RewriteAction.SWITCH_KEYWORDS,
            3: RewriteAction.REPHRASE,
        }
        action = action_map.get(retry_count, RewriteAction.REPHRASE)
        query = await rewrite_query(client, query, action)

    state["retrieval_strategy"] = strategy

    total_steps = state["total_steps"]
    retr_progress = 0.10 + (step_idx / max(total_steps, 1)) * 0.30

    # ── Local Retrieval ──
    local_results = []
    if data_source in ("local", "both"):
        emit(task_id, "retrieval_start", {
            "step": step_idx + 1,
            "total": total_steps,
            "query": query,
            "strategy": strategy,
            "data_source": "local",
            "retry_count": retry_count,
            "progress": retr_progress,
        })

        vector_store = state.get("_vector_store") or _get_vector_store()
        bm25 = state.get("_bm25") or _get_bm25()

        if not bm25.is_indexed:
            strategy = "semantic"

        hybrid = HybridRetriever(vector_store, bm25)
        top_k = settings.retrieval.top_k * (2 ** retry_count)

        if strategy == "semantic":
            results = hybrid.search_vector_only(query, top_k=top_k)
        elif strategy == "keyword":
            results = hybrid.search_keyword_only(query, top_k=top_k)
        else:
            results = hybrid.search(query, top_k=top_k)

        local_results = [
            {
                "chunk_id": r.chunk_id,
                "content": r.content,
                "score": r.combined_score,
                "vector_score": r.vector_score,
                "bm25_score": r.bm25_score,
                "metadata": {
                    **r.metadata,
                    "strategy": strategy,
                    "source": "local",
                },
            }
            for r in results
        ]

        emit(task_id, "retrieval_result", {
            "step": step_idx + 1,
            "result_count": len(local_results),
            "top_score": local_results[0]["score"] if local_results else 0,
            "top_preview": local_results[0]["content"][:200] if local_results else "",
            "data_source": "local",
            "progress": retr_progress + 0.10,
        })

    # ── Web Search ──
    web_results = []
    if data_source in ("web", "both"):
        emit(task_id, "web_search_start", {
            "step": step_idx + 1,
            "total": total_steps,
            "query": query,
            "progress": retr_progress + 0.10,
        })

        from research_agent.tools.web_search import search_web
        web_results = await search_web(query)

        emit(task_id, "web_search_result", {
            "step": step_idx + 1,
            "result_count": len(web_results),
            "top_url": web_results[0]["metadata"]["url"] if web_results else "",
            "top_preview": web_results[0]["content"][:200] if web_results else "",
            "progress": retr_progress + 0.15,
        })

    # ── Merge: local first, then web ──
    all_results = local_results + web_results
    state["retrieval_results"] = all_results

    combined_progress = 0.10 + ((step_idx + 1) / max(total_steps, 1)) * 0.30
    emit(task_id, "retrieval_combined", {
        "step": step_idx + 1,
        "local_count": len(local_results),
        "web_count": len(web_results),
        "total_count": len(all_results),
        "progress": combined_progress,
    })

    return state
```

- [ ] **Step 2: 验证检索节点导入正确**

```bash
python3 -c "
from research_agent.graph import build_graph
graph = build_graph()
print('Graph built OK, nodes:', list(graph.nodes.keys()))
"
```

Expected: `Graph built OK, nodes: ['decomposition', 'retrieval', 'critique', 'synthesis']`

- [ ] **Step 3: Commit**

```bash
git add research_agent/graph.py
git commit -m "feat: integrate web search into retrieval node with data_source routing"
```

---

### Task 7: 在 FastAPI 生命周期中管理 MCP 连接

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 修改 `backend/main.py` 的 lifespan**

```python
# backend/main.py — 修改 lifespan 函数和 import

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.research import router as research_router
from backend.routers.quick_search import router as quick_search_router
from backend.routers.documents import router as documents_router
from backend.routers.settings import router as settings_router
from research_agent.tools.mcp_client import mcp_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect MCP client. Shutdown: disconnect."""
    await mcp_client.connect()
    yield
    await mcp_client.disconnect()


app = FastAPI(
    title="Deep Research Agent",
    description="Agentic RAG — autonomous query decomposition, adaptive retrieval, quality critique, and report synthesis",
    version="0.1.0",
    lifespan=lifespan,
)

# ... 其余代码不变 (CORS, routers, health_check) ...
```

- [ ] **Step 2: 验证 FastAPI 启动不报错**

```bash
python3 -c "
from backend.main import app
print('FastAPI app created:', app.title)
"
```

Expected: `FastAPI app created: Deep Research Agent`

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: wire MCP client lifecycle into FastAPI startup/shutdown"
```

---

### Task 8: 编写集成测试

**Files:**
- Create: `tests/test_web_search.py`

- [ ] **Step 1: 创建测试文件 `tests/test_web_search.py`**

```python
"""Tests for MCP web search integration."""

import pytest

from research_agent.tools.web_search import search_web
from research_agent.tools.mcp_client import MCPClient


class TestWebSearchTool:
    """Tests for search_web without requiring actual MCP connection."""

    @pytest.mark.asyncio
    async def test_search_web_returns_empty_when_not_configured(self, monkeypatch):
        """search_web returns [] when TAVILY_API_KEY is empty."""
        monkeypatch.setattr("config.settings.mcp.tavily_api_key", "")
        results = await search_web("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_web_returns_empty_when_mcp_fails(self, monkeypatch):
        """search_web returns [] when MCP call raises an exception."""
        monkeypatch.setattr("config.settings.mcp.tavily_api_key", "fake-key")

        async def mock_call_tool(*args, **kwargs):
            raise RuntimeError("connection failed")

        monkeypatch.setattr(
            "research_agent.tools.web_search.mcp_client.call_tool",
            mock_call_tool,
        )
        results = await search_web("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_web_normalizes_results(self, monkeypatch):
        """search_web transforms Tavily results into agent format."""
        monkeypatch.setattr("config.settings.mcp.tavily_api_key", "fake-key")

        tavily_response = '[{"title": "Test Page", "url": "https://example.com", "content": "Hello world", "score": 0.95}]'

        async def mock_call_tool(*args, **kwargs):
            return tavily_response

        monkeypatch.setattr(
            "research_agent.tools.web_search.mcp_client.call_tool",
            mock_call_tool,
        )
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
```

- [ ] **Step 2: 运行测试验证全部通过**

```bash
pytest tests/test_web_search.py -v
```

Expected: 4 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_web_search.py
git commit -m "test: add unit tests for web search tool and MCP client"
```

---

### Task 9: 端到端验证

- [ ] **Step 1: 启动后端验证 MCP 连接日志**

先不配置 Tavily key，验证降级行为：

```bash
# 启动后端
uvicorn backend.main:app --port 8000 &
sleep 3

# 检查日志：应该看到 "[MCP] TAVILY_API_KEY not set, skipping MCP connection"
# 确认 /health 正常
curl -s http://localhost:8000/health

# 停止
kill %1 2>/dev/null
```

Expected: `/health` 返回 `{"status":"ok","version":"0.1.0"}`，日志显示跳过 MCP

- [ ] **Step 2: 配置 Tavily key 后验证完整流程**

```bash
# 在 config/.env 中添加真实的 Tavily API Key
echo "MCP_TAVILY_API_KEY=tvly-your-real-key" >> config/.env
echo "MCP_WEB_SEARCH_ENABLED=true" >> config/.env

# 重新启动后端
uvicorn backend.main:app --port 8000 &
sleep 3

# 检查日志应显示 "[MCP] Connected. Available tools: ['web_search']"
```

- [ ] **Step 3: 提交研究任务，验证 web search 触发**

```bash
# 提交一个需要实时信息的问题
curl -s -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "2026年最近AI领域有什么重要进展？"}' | python3 -m json.tool

# 获取 task_id，订阅 SSE stream
# curl -N http://localhost:8000/api/v1/research/<task_id>/stream
# 应该能看到 web_search_start / web_search_result 事件
```

Expected: 当问题需要实时信息时，分解器会自动将 `data_source` 设为 `"web"` 或 `"both"`，检索节点发出 `web_search_start` 和 `web_search_result` 事件

- [ ] **Step 4: 清理测试 key**

```bash
# 从 .env 中移除测试 key
# 恢复 .env 文件
git checkout config/.env 2>/dev/null || true
```

- [ ] **Step 5: Commit（如有变更）**

```bash
git status
```

---

### Task 10: 更新配置模板

- [ ] **Step 1: 确认 .env.example 已更新**

在 Task 1 已更新，确认：

```bash
grep -A 4 "MCP" config/.env.example
```

Expected: 显示 MCP 相关配置项

- [ ] **Step 2: 最终验证全部已有测试仍然通过**

```bash
pytest tests/ -v
```

Expected: 30 passed (原有 26 + 新增 4)

- [ ] **Step 3: 最终 Commit**

```bash
git add -A
git diff --cached --stat
git commit -m "feat: complete MCP web search integration with tests and config"
```

---

### Task 11: 后端 — 从 API 到 Agent 传递 enable_web_search 开关

**Files:**
- Modify: `backend/routers/research.py`
- Modify: `research_agent/state.py`
- Modify: `research_agent/graph.py:46-89` (decomposition_node)
- Modify: `research_agent/planner/decomposer.py` (更新 _build_system_prompt 和 decompose_query 签名)

- [ ] **Step 1: 在 ResearchState 中添加 enable_web_search 字段**

`research_agent/state.py` — 在 `ResearchState` 类中添加一行：

```python
class ResearchState(TypedDict, total=False):
    # Input
    query: str
    task_id: str
    enable_web_search: bool  # ← 新增：前端开关

    # ... 其余不变
```

- [ ] **Step 2: 在 ResearchRequest 中添加 enable_web_search**

`backend/routers/research.py` — 修改 `ResearchRequest` 和 `submit_research`：

```python
class ResearchRequest(BaseModel):
    query: str
    enable_web_search: bool = False  # ← 新增，默认关闭


@router.post("", response_model=ResearchResponse)
async def submit_research(req: ResearchRequest):
    """Submit a new research task."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    task_id = event_bus.create_task()

    task_manager.create_task(task_id, req.query)
    task_manager.update_status(task_id, TaskStatus.RUNNING)

    # 传递 enable_web_search 到 agent
    asyncio.create_task(_run_agent(task_id, req.query, req.enable_web_search))

    import sys
    web_flag = "ON" if req.enable_web_search else "OFF"
    print(f"[ROUTER] Task {task_id} submitted, query={req.query[:60]}, web={web_flag}",
          flush=True, file=sys.stderr)

    return ResearchResponse(
        success=True,
        data={"task_id": task_id},
    )
```

- [ ] **Step 3: 修改 _run_agent 接收并传递 enable_web_search**

`backend/routers/research.py` — 修改 `_run_agent` 函数签名和 initial_state：

```python
async def _run_agent(task_id: str, query: str, enable_web_search: bool = False):
    """Execute the agent graph for a research task."""
    import sys, time
    current_task = asyncio.current_task()
    if current_task:
        task_manager.register_task(task_id, current_task)

    try:
        print(f"[AGENT {task_id}] _run_agent START, query={query[:60]}, web={enable_web_search}",
              flush=True, file=sys.stderr)
        initial_state = {
            "query": query,
            "task_id": task_id,
            "enable_web_search": enable_web_search,  # ← 传递开关
        }
        # ... 其余代码不变 ...
```

- [ ] **Step 4: 修改 decomposer 接受 enable_web_search 参数**

`research_agent/planner/decomposer.py` — 修改 `_build_system_prompt` 和 `decompose_query`：

```python
def _build_system_prompt(enable_web_search: bool = False) -> str:
    """Build the decomposition prompt.

    enable_web_search: 前端开关 + API Key 双重控制。
        只有开关开启 AND API Key 已配置时，才告诉 LLM 可以使用 web 搜索。
    """
    web_available = enable_web_search and bool(settings.mcp.tavily_api_key)

    web_instruction = (
        '- "web": 需要实时信息、最新数据或知识库没有覆盖的知识（联网搜索当前可用）\n- "both": 本地知识库和联网搜索都需要，互补使用'
        if web_available else
        '- "web": 当前不可用，请勿选择\n- "both": 当前不可用，请勿选择。如需联网信息，选择 "local"'
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
```

- [ ] **Step 5: 修改 decomposition_node 传递 enable_web_search**

`research_agent/graph.py` — 在 `decomposition_node` 中，修改 `decompose_query` 调用：

```python
async def decomposition_node(state: ResearchState) -> ResearchState:
    """Decompose the user query into sub-questions and create a research plan."""
    task_id = state.get("task_id", "")
    query = state["query"]
    enable_web_search = state.get("enable_web_search", False)  # ← 从 state 读取

    _dbg(task_id, "decomposition_node ENTER")
    emit(task_id, "research_plan_start", {"query": query, "progress": 0.05})

    _dbg(task_id, "creating LLM client...")
    client = create_llm_client()
    _dbg(task_id, f"calling decompose_query (model={client.model}, web={enable_web_search})...")
    t0 = _time.time()
    try:
        sub_queries = await decompose_query(client, query, enable_web_search)  # ← 传递开关
        _dbg(task_id, f"decompose_query OK after {_time.time()-t0:.1f}s, {len(sub_queries)} sub-queries")
    except Exception as e:
        _dbg(task_id, f"decompose_query FAILED after {_time.time()-t0:.1f}s: {e}")
        raise

    # ... 其余代码不变（plan 构建、emit 等）...
```

- [ ] **Step 6: 验证后端导入和类型正确**

```bash
python3 -c "
from research_agent.state import ResearchState
print('ResearchState fields:', [k for k in ResearchState.__annotations__])
print('enable_web_search' in ResearchState.__annotations__)
"
```

Expected: `enable_web_search in ResearchState.__annotations__` → `True`

- [ ] **Step 7: Commit**

```bash
git add backend/routers/research.py research_agent/state.py research_agent/graph.py research_agent/planner/decomposer.py
git commit -m "feat: add enable_web_search toggle from API through to decomposer"
```

---

### Task 12: 前端 — 添加网络搜索开关

**Files:**
- Modify: `frontend-vue/src/api/research.ts`
- Modify: `frontend-vue/src/composables/useResearch.ts`
- Modify: `frontend-vue/src/stores/research.ts`
- Modify: `frontend-vue/src/components/research/SearchForm.vue`
- Modify: `frontend-vue/src/pages/ResearchPage.vue`

- [ ] **Step 1: 修改 API 层 — `submitResearch` 传递开关**

`frontend-vue/src/api/research.ts` — 修改函数签名和请求体：

```typescript
export async function submitResearch(
  query: string,
  enableWebSearch: boolean = false,
): Promise<string> {
  const resp = await fetch(`${BASE}/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      enable_web_search: enableWebSearch,
    }),
  })
  if (!resp.ok) {
    throw new Error(`提交失败: ${resp.status} ${resp.statusText}`)
  }
  const body: TaskResponse = await resp.json()
  if (!body.success || !body.data?.task_id) {
    throw new Error(body.error || '提交失败：未获取到任务 ID')
  }
  return body.data.task_id
}
```

- [ ] **Step 2: 修改 useResearch — 传递开关到 API**

`frontend-vue/src/composables/useResearch.ts` — 修改 `start` 函数签名：

```typescript
export function useResearch() {
  const store = useResearchStore()
  let eventSource: EventSource | null = null

  async function start(query: string, enableWebSearch: boolean = false): Promise<void> {
    store.reset()
    store.setQuery(query)

    try {
      const taskId = await submitResearch(query, enableWebSearch)
      store.startResearch(taskId)

      // ... 其余代码不变 ...
    }
  }

  // ... stop, fetchFinalResult, cleanup 不变 ...
}
```

- [ ] **Step 3: 在 store 中处理新增的 SSE 事件**

`frontend-vue/src/stores/research.ts` — 在 `summarizeEvent` 和 `handleEvent` 中添加 web search 事件处理：

```typescript
// 在 summarizeEvent 的 switch 中添加：
case 'web_search_start':
  return `联网搜索: ${(data.query as string || '').slice(0, 50)}`
case 'web_search_result':
  return `联网搜索完成: ${data.result_count} 条结果`
case 'retrieval_combined':
  return `检索汇总: 本地 ${data.local_count} + 网络 ${data.web_count} = ${data.total_count} 条`

// 在 handleEvent 的 switch 中添加：
case 'web_search_start':
  currentDetail.value = `正在联网搜索: ${(data.query as string || '').slice(0, 40)}...`
  break

case 'web_search_result': {
  currentDetail.value = `联网搜索完成，找到 ${data.result_count} 条结果`
  break
}

case 'retrieval_combined': {
  const local = data.local_count as number || 0
  const web = data.web_count as number || 0
  currentDetail.value = `检索完成: 本地 ${local} + 网络 ${web} = ${data.total_count} 条`
  break
}
```

- [ ] **Step 4: 在 SearchForm 中添加开关组件**

`frontend-vue/src/components/research/SearchForm.vue` —

在 template 中，按钮组上方添加开关（放在 textarea 和按钮之间）：

```html
<template>
  <div class="mb-5">
    <n-card :bordered="false" class="search-card">
      <div class="flex items-start gap-3">
        <div class="flex-1">
          <n-input
            v-model:value="inputText"
            type="textarea"
            placeholder="输入你的研究问题，例如：人工智能在医疗影像和药物研发中的应用有什么区别？"
            :autosize="{ minRows: 2, maxRows: 4 }"
            :disabled="isRunning"
            size="large"
            round
            @keydown.enter.ctrl="emitSubmit"
          />
        </div>
        <div class="flex items-center gap-2 flex-shrink-0">
          <n-button
            type="primary"
            size="large"
            :disabled="!inputText.trim() || isRunning"
            :loading="isRunning"
            @click="emitSubmit"
          >
            <template #icon><n-icon><rocket-outline /></n-icon></template>
            {{ isRunning ? '研究中...' : '开始研究' }}
          </n-button>
          <n-button
            v-if="isRunning"
            type="error"
            size="large"
            secondary
            @click="$emit('stop')"
          >
            <template #icon><n-icon><stop-circle-outline /></n-icon></template>
            停止
          </n-button>
        </div>
      </div>

      <!-- 新增：网络搜索开关 -->
      <div class="flex items-center gap-3 mt-3">
        <n-switch
          v-model:value="enableWebSearch"
          :disabled="isRunning"
          size="small"
        />
        <span class="text-xs text-gray-500">
          联网搜索
          <span class="text-gray-400 ml-1">
            {{ enableWebSearch ? '已开启：将获取实时信息辅助研究' : '已关闭：仅使用本地知识库' }}
          </span>
        </span>
      </div>

      <div v-if="!isRunning" class="flex flex-wrap gap-2 mt-3">
        <span
          v-for="(ex, i) in examples"
          :key="i"
          class="example-chip"
          @click="selectExample(ex)"
        >
          💡 {{ ex.slice(0, 30) }}{{ ex.length > 30 ? '…' : '' }}
        </span>
      </div>
    </n-card>
  </div>
</template>
```

在 `<script setup>` 中更新 emit 类型和状态：

```typescript
<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  isRunning: boolean
}>()

const emit = defineEmits<{
  submit: [query: string, enableWebSearch: boolean]
  stop: []
}>()

const examples = [
  '人工智能在医疗影像和药物研发中的应用有什么区别？',
  'Transformer架构相比LSTM在自然语言处理中有哪些优势？',
  '量子计算的发展对现代密码学构成多大的威胁？',
  'CRISPR基因编辑技术在遗传病治疗中的前景和伦理挑战是什么？',
  '固态电池技术相比传统锂电池的核心突破点在哪里？',
]

const inputText = ref(examples[0])
const enableWebSearch = ref(false)

function emitSubmit() {
  const q = inputText.value.trim()
  if (q) {
    emit('submit', q, enableWebSearch.value)
  }
}

function selectExample(text: string) {
  inputText.value = text
}
</script>
```

- [ ] **Step 5: 修改 ResearchPage 传递开关**

`frontend-vue/src/pages/ResearchPage.vue` — 修改 `onSubmit` 函数签名：

```typescript
async function onSubmit(query: string, enableWebSearch: boolean) {
  await start(query, enableWebSearch)
}
```

- [ ] **Step 6: 验证前端编译通过**

```bash
cd frontend-vue && npm run build --if-present 2>&1 | tail -5
# 或者至少检查 TypeScript 类型
npx vue-tsc --noEmit 2>&1 | tail -10
```

Expected: 无编译错误

- [ ] **Step 7: Commit**

```bash
git add frontend-vue/src/api/research.ts \
        frontend-vue/src/composables/useResearch.ts \
        frontend-vue/src/stores/research.ts \
        frontend-vue/src/components/research/SearchForm.vue \
        frontend-vue/src/pages/ResearchPage.vue
git commit -m "feat: add web search toggle switch on research page"
```

---

### Task 13: 端到端验证 — 开关控制 Web Search

- [ ] **Step 1: 不配置 Tavily Key，验证开关始终不触发 Web Search**

```bash
# 确保没有配置 Tavily Key
grep TAVILY config/.env 2>/dev/null || echo "No Tavily key configured"

# 启动后端
uvicorn backend.main:app --port 8000 &
sleep 3

# 发送请求：开关打开（但由于无 API Key，不应触发 web search）
curl -s -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "2026年AI最新进展", "enable_web_search": true}'

# 订阅 SSE 查看事件，不应出现 web_search_start
```

Expected: 即使 `enable_web_search: true`，因为没配 Tavily Key，分解器仍只标记 `data_source: local`

- [ ] **Step 2: 配置 Tavily Key，验证开关关闭时不触发**

```bash
# 配置 Tavily key
echo "MCP_TAVILY_API_KEY=tvly-your-real-key" >> config/.env

# 重启
kill %1 2>/dev/null
uvicorn backend.main:app --port 8000 &
sleep 3

# 发送请求：开关关闭 → 即使有 API Key，也不应触发 web search
curl -s -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "2026年AI最新进展", "enable_web_search": false}'
```

Expected: `enable_web_search: false` → 分解器只标记 `data_source: local`，无 web search 事件

- [ ] **Step 3: 开关开启 + API Key 配置 → Web Search 生效**

```bash
curl -s -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "2026年AI最新进展", "enable_web_search": true}'
```

Expected: 分解器可能标记 `data_source: web` 或 `both`，SSE 流中出现 `web_search_start` / `web_search_result` 事件

- [ ] **Step 4: 清理并运行全部测试**

```bash
kill %1 2>/dev/null
git checkout config/.env 2>/dev/null || true
pytest tests/ -v
```

Expected: 全部测试通过（包括新增的 test_web_search.py）

- [ ] **Step 5: Commit**

```bash
git status
```

---

### Task 14: 后端 — 增强 SSE 事件，携带完整网页抓取结果

**Files:**
- Modify: `research_agent/graph.py` (retrieval_node 中的 web_search_result emit)

- [ ] **Step 1: 修改 web_search_result SSE 事件数据**

`research_agent/graph.py` — 在 `retrieval_node` 的 Web Search 部分，替换 `emit(task_id, "web_search_result", ...)` 为：

```python
    # ── Web Search ──
    web_results = []
    if data_source in ("web", "both"):
        emit(task_id, "web_search_start", {
            "step": step_idx + 1,
            "total": total_steps,
            "query": query,
            "progress": retr_progress + 0.10,
        })

        from research_agent.tools.web_search import search_web
        web_results = await search_web(query)

        # 构建结构化结果列表，前端可直接渲染
        web_result_items = [
            {
                "title": r["metadata"].get("title", ""),
                "url": r["metadata"].get("url", ""),
                "content": r["content"][:200],
                "score": r["score"],
            }
            for r in web_results
        ]

        emit(task_id, "web_search_result", {
            "step": step_idx + 1,
            "result_count": len(web_results),
            "results": web_result_items,
            "progress": retr_progress + 0.15,
        })
```

- [ ] **Step 2: 确认 JSON 序列化安全**

`score` 是 float（可能为 None），`url` 和 `title` 是字符串。SSE 传输时 `json.dumps` 会正常处理。验证：

```bash
python3 -c "
import json
items = [{'title': 'Test', 'url': 'https://x.com', 'content': 'hello'[:200], 'score': 0.95}]
print(json.dumps({'results': items}, ensure_ascii=False)[:100])
"
```

Expected: 正常输出 JSON 字符串

- [ ] **Step 3: Commit**

```bash
git add research_agent/graph.py
git commit -m "feat: include full web search results in SSE event for real-time display"
```

---

### Task 15: 前端 — 实时展示抓取的网页内容

**Files:**
- Create: `frontend-vue/src/components/research/WebSearchCard.vue`
- Modify: `frontend-vue/src/stores/research.ts`
- Modify: `frontend-vue/src/pages/ResearchPage.vue`

- [ ] **Step 1: 在 store 中添加 webSearchResults 状态和事件处理**

`frontend-vue/src/stores/research.ts` —

a) 在 interface 区域添加类型：

```typescript
export interface WebSearchResultItem {
  title: string
  url: string
  content: string
  score: number
}
```

b) 在 store 中添加状态和 handler：

```typescript
// 在 store 的 ref 区域添加：
const webSearchResults = ref<WebSearchResultItem[]>([])

// 在 reset() 函数中添加重置：
function reset() {
  // ... 现有重置代码 ...
  webSearchResults.value = []
}

// 在 handleEvent 的 switch 中添加：
case 'web_search_start':
  currentDetail.value = `正在联网搜索: ${(data.query as string || '').slice(0, 40)}...`
  webSearchResults.value = []  // 清空上一轮的结果
  break

case 'web_search_result': {
  const results = (data.results as WebSearchResultItem[]) || []
  webSearchResults.value = results
  const urls = results.map((r: WebSearchResultItem) => r.url).join(', ')
  currentDetail.value = `联网搜索完成，抓到 ${results.length} 个网页: ${urls.slice(0, 80)}`
  break
}

// 在 return 中添加：
webSearchResults,
```

- [ ] **Step 2: 创建 WebSearchCard 组件**

`frontend-vue/src/components/research/WebSearchCard.vue`：

```html
<template>
  <n-card
    v-if="store.webSearchResults.length > 0"
    title="🌐 网络搜索结果"
    size="small"
    :bordered="false"
    class="mb-3"
  >
    <template #header-extra>
      <n-tag size="small" type="info">{{ store.webSearchResults.length }} 个网页</n-tag>
    </template>

    <div class="max-h-80 overflow-y-auto">
      <div
        v-for="(item, i) in store.webSearchResults"
        :key="i"
        class="web-result-item"
      >
        <div class="flex items-start gap-2">
          <span class="text-xs text-gray-300 font-mono flex-shrink-0 pt-0.5">
            {{ i + 1 }}.
          </span>
          <div class="min-w-0">
            <a
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline truncate block"
            >
              {{ item.title || '无标题' }}
            </a>
            <p class="text-xs text-gray-500 mt-0.5 line-clamp-2">
              {{ item.content }}
            </p>
            <div class="flex items-center gap-2 mt-1">
              <span class="text-xs text-gray-300 truncate max-w-[200px]">
                {{ item.url }}
              </span>
              <ScoreBadge v-if="item.score" :score="item.score" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { useResearchStore } from '@/stores/research'
import ScoreBadge from '@/components/common/ScoreBadge.vue'

const store = useResearchStore()
</script>

<style scoped>
.web-result-item {
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
}
.web-result-item:last-child {
  border-bottom: none;
}
</style>
```

- [ ] **Step 3: 在 ResearchPage 中引入 WebSearchCard**

`frontend-vue/src/pages/ResearchPage.vue` —

a) 在 import 区域添加：

```typescript
import WebSearchCard from '@/components/research/WebSearchCard.vue'
```

b) 在模板中，`ProgressPanel` 之后、`EventTimeline` 之前插入：

```html
<div class="lg:col-span-1">
  <AgentStepper />
  <ProgressPanel />
  <WebSearchCard />       <!-- ← 新增 -->
  <EventTimeline />
</div>
```

- [ ] **Step 4: 验证前端编译**

```bash
cd frontend-vue && npx vue-tsc --noEmit 2>&1 | tail -10
```

Expected: 无类型错误

- [ ] **Step 5: Commit**

```bash
git add frontend-vue/src/components/research/WebSearchCard.vue \
        frontend-vue/src/stores/research.ts \
        frontend-vue/src/pages/ResearchPage.vue
git commit -m "feat: add real-time web search results card in research page"
```

---

## 架构总结

### 实时 Web Search 数据流

```
SSE: web_search_result
  └─ { step, result_count, results: [{title, url, content, score}, ...] }
       │
       ▼
  store.handleEvent("web_search_result", data)
       │
       ├─ store.webSearchResults = data.results  ← 实时更新
       ├─ currentDetail = "联网搜索完成，抓到 N 个网页: url1, url2..."
       └─ eventLog.push(summary)
       │
       ▼
  WebSearchCard 组件 (响应式绑定 store.webSearchResults)
  ┌──────────────────────────────────────────┐
  │ 🌐 网络搜索结果                    [3个网页] │
  │                                            │
  │ 1. AI最新进展综述                           │
  │    https://example.com/ai-2026              │
  │    2026年人工智能在多模态、Agent、具身...     │
  │    [Score: 0.92]                            │
  │                                            │
  │ 2. GPT-5发布...                            │
  │    https://...                              │
  └──────────────────────────────────────────┘
```

### 开关控制流

```
前端 SearchForm (n-switch)
  └─ enableWebSearch: boolean
       │
       ▼
  ResearchPage → useResearch.start(query, enableWebSearch)
       │
       ▼
  API: submitResearch(query, enable_web_search)
       │
       ▼
  Backend: POST /api/v1/research { query, enable_web_search }
       │
       ▼
  _run_agent(task_id, query, enable_web_search)
       │
       ▼
  initial_state = { query, task_id, enable_web_search }
       │
       ▼
  decomposition_node:
    enable_web_search = state.get("enable_web_search", False)
    sub_queries = decompose_query(client, query, enable_web_search)
       │
       ▼
  _build_system_prompt(enable_web_search):
    web_available = enable_web_search AND bool(settings.mcp.tavily_api_key)
       │
       ├─ web_available=True  → LLM 可选择 "web" / "both"
       └─ web_available=False → LLM 只能选 "local"
```

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Process                            │
│                                                                  │
│  backend/main.py (lifespan)                                     │
│  ├─ startup:  mcp_client.connect()                              │
│  └─ shutdown: mcp_client.disconnect()                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  LangGraph Agent                                          │   │
│  │                                                           │   │
│  │  Decomposition                                            │   │
│  │  └─ 每个子问题标记 data_source: local | web | both         │   │
│  │                                                           │   │
│  │  Retrieval                                                │   │
│  │  ├─ data_source=local → Chroma/BM25 本地检索              │   │
│  │  ├─ data_source=web   → MCP call_tool("web_search")       │   │
│  │  └─ data_source=both  → 本地 + Web 合并                   │   │
│  │                                                           │   │
│  │  Critique → Synthesis → Citation (无需修改)               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  research_agent/tools/mcp_client.py                              │
│  └─ stdio_client → MCP Server subprocess                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                    stdio (JSON-RPC)
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│  MCP Server (mcp_servers/web_search/server.py)                  │
│                                                                  │
│  Tools:                                                          │
│  └─ web_search(query, max_results) → Tavily API → JSON results  │
└─────────────────────────────────────────────────────────────────┘
```

**降级策略：**
- 无 Tavily API Key → Decomposer 只建议 `data_source=local` → Web search 从不触发
- MCP Server 启动失败 → `mcp_client.connect()` 捕获异常，`is_connected=False`
- 单次 Web search 失败 → `search_web()` 返回 `[]`，Agent 仅使用本地结果
- 所有错误均静默降级，不中断 Agent 执行
