# Deep Research Agent

## Tech Stack
- Backend: Python 3.12+, FastAPI
- Agent Framework: LangGraph
- Vector DB: Milvus (primary), Chroma (lightweight fallback)
- Embedding: BGE-large-v2 or all-MiniLM-L6-v2
- LLM: Qwen / OpenAI-compatible / SiliconFlow (multi-provider)
- Knowledge Graph: NetworkX (lightweight, prototype) → Neo4j (production)
- Tracing: LangFuse
- Evaluation: RAGAS
- Frontend: Streamlit (MVP) → Vue 3 (production)
- MCP: MCP protocol for data source integration

## Project Structure
```
deep-research-agent/
├── backend/                  # FastAPI backend
│   ├── routers/              # API routes
│   └── services/             # Business logic + streaming
├── research_agent/           # Core agent logic
│   ├── planner/              # Query decomposition + research planning
│   ├── retrieval/            # Adaptive retrieval (vector + BM25 + web)
│   ├── critique/             # Retrieval quality assessment + self-correction
│   ├── synthesis/            # Multi-source aggregation + report generation
│   ├── kg/                   # Knowledge graph construction + multi-hop reasoning
│   ├── llm/                  # LLM client (multi-provider)
│   ├── mcp_tools/            # MCP data source tools
│   ├── memory/               # Agent memory (short-term + long-term)
│   └── evaluation/           # RAGAS + custom metrics
├── frontend/                 # Streamlit MVP frontend
├── data/                     # Sample documents + test datasets
├── config/                   # YAML configs + .env
└── tests/                    # Unit + integration tests
```

## Core Features (Progressive)
1. **MVP**: Query decomposition → Adaptive retrieval → Quality critique → Report synthesis
2. **V2**: Knowledge graph construction + multi-hop reasoning
3. **V3**: MCP multi-source integration + agent memory system
4. **V4**: Evaluation dashboard + LangFuse tracing

## Code Conventions
- Python: PEP 8, type hints required
- LangGraph: Each agent node = single responsibility
- Config: YAML + pydantic-settings
- API: JSON with `{success, data, error}` envelope
- Streaming: SSE (Server-Sent Events)
- Testing: pytest + pytest-asyncio
