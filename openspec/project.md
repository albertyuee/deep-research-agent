# Deep Research Agent

## Tech Stack
- Backend: Python 3.12+, FastAPI
- Agent Framework: LangGraph (StateGraph + conditional routing)
- Vector DB: ChromaDB (local), Zilliz Cloud / Milvus (remote)
- Embedding: BAAI/bge-large-zh-v1.5 (1024-dim, via SiliconFlow API)
- LLM: Qwen / OpenAI-compatible / SiliconFlow (multi-provider)
- MCP Web Search: Tavily Search API via MCP protocol (stdio transport)
- Knowledge Graph: NetworkX → Neo4j (V2)
- Tracing: LangFuse (planned)
- Evaluation: RAGAS (planned)
- Frontend: Vue 3 + Vite + Naive UI

## Project Structure
```
deep-research-agent/
├── backend/                  # FastAPI backend
│   ├── routers/              # API routes (research, quick_search, documents, settings)
│   └── services/             # Business logic + streaming
├── research_agent/           # Core agent logic
│   ├── planner/              # Query decomposition + research planning
│   ├── retrieval/            # Adaptive retrieval (vector + BM25 + web)
│   ├── critique/             # Retrieval quality assessment + self-correction
│   ├── synthesis/            # Multi-source aggregation + report generation
│   ├── tools/                # MCP client + web search tool
│   ├── llm/                  # LLM client (multi-provider)
│   └── streaming.py          # SSE event bus
├── mcp_servers/              # MCP server implementations
│   └── web_search/           # Tavily Search MCP server (stdio)
├── frontend-vue/             # Vue 3 frontend
│   └── src/
│       ├── pages/            # ResearchPage, QuickSearchPage, DocumentsPage, SettingsPage
│       ├── components/       # Research, chat, report, settings components
│       ├── stores/           # Pinia stores (research, chat, settings)
│       ├── composables/      # useResearch (SSE streaming)
│       └── api/              # Backend API call layer
├── data/                     # Sample documents + ChromaDB persistent data
├── config/                   # pydantic-settings + .env
└── tests/                    # Unit + integration tests (30 cases)
```

## Core Features
1. **MVP** (completed): Query decomposition → Adaptive retrieval → Quality critique → Report synthesis
2. **Web Search** (completed): MCP-based Tavily Search with agent-driven data source routing, frontend toggle
3. **Remote Vector Store** (completed): Zilliz Cloud / self-hosted Milvus backend, auto-dimension detection
4. **V2**: Knowledge graph construction + multi-hop reasoning
5. **V3**: Additional MCP tools (GitHub, Notion, etc.) + agent memory system

## Code Conventions
- Python: PEP 8, type hints required
- LangGraph: Each agent node = single responsibility
- Config: pydantic-settings + .env
- API: JSON with `{success, data, error}` envelope
- Streaming: SSE (Server-Sent Events)
- Testing: pytest + pytest-asyncio
