## 1. MCP Configuration & Server

- [x] 1.1 Add MCPSettings to config/settings.py (tavily_api_key, web_search_enabled)
- [x] 1.2 Add MCP env vars to config/.env.example
- [x] 1.3 Create mcp_servers/web_search/server.py (MCP server wrapping Tavily API)
- [x] 1.4 Create mcp_servers/web_search/__main__.py entry point
- [x] 1.5 Add mcp>=1.27.0 and httpx>=0.25.0 to pyproject.toml dependencies

## 2. MCP Client & Web Search Tool

- [x] 2.1 Create research_agent/tools/mcp_client.py (MCPClient singleton, stdio lifecycle)
- [x] 2.2 Create research_agent/tools/web_search.py (search_web with normalized result format)
- [x] 2.3 Wire MCP connect/disconnect into FastAPI lifespan (backend/main.py)

## 3. Agent Integration

- [x] 3.1 Modify decomposer: add data_source field to prompt + schema (local/web/both)
- [x] 3.2 Modify retrieval_node: route by data_source, merge local + web results
- [x] 3.3 Add web_search_start / web_search_result / retrieval_combined SSE events
- [x] 3.4 Add enable_web_search to ResearchState and pass from API → agent
- [x] 3.5 Add ResearchRequest.enable_web_search to backend router
- [x] 3.6 Handle null content from Tavily API (r.get("content") or "")
- [x] 3.7 Add ChromaDB failure fallback: try/except → web results when data_source="both"

## 4. Milvus / Zilliz Cloud Vector Store

- [x] 4.1 Add MILVUS_URI and MILVUS_TOKEN to MilvusSettings
- [x] 4.2 Create MilvusVectorStore with search/add_documents/count interface
- [x] 4.3 Auto-detect embedding dimension in _ensure_collection()
- [x] 4.4 Use auto_id=True and store chunk_id as varchar field
- [x] 4.5 Create create_vector_store() factory function
- [x] 4.6 Update graph.py and quick_search.py to use factory

## 5. Settings Page Enhancements

- [x] 5.1 Add milvus settings to GET /api/v1/settings response
- [x] 5.2 Add milvus fields to PATCH path_map (uri, token, host, port)
- [x] 5.3 Fix masked token skip logic (also skip "token" field, not just "api_key")
- [x] 5.4 Update system-info to report active vector_backend and chunk_count
- [x] 5.5 Add POST /api/v1/settings/test-connection endpoint (llm/embedding/milvus)
- [x] 5.6 Add MilvusSettings and SystemInfo types to frontend api/settings.ts
- [x] 5.7 Add vector store radio selector to SettingsPage.vue
- [x] 5.8 Add Zilliz Cloud / self-hosted Milvus config fields
- [x] 5.9 Add test connection buttons with loading/success/error states
- [x] 5.10 Redesign settings page layout with FormField component, better spacing
- [x] 5.11 Add header-extra slot to SettingsSection component

## 6. Frontend Web Search Display

- [x] 6.1 Add enableWebSearch switch to SearchForm.vue
- [x] 6.2 Pass enableWebSearch through ResearchPage → useResearch → API
- [x] 6.3 Add webSearchResults state and event handlers to research store
- [x] 6.4 Create WebSearchCard.vue for real-time web results display
- [x] 6.5 Handle web_search_start/result/retrieval_combined events in store

## 7. Testing & Verification

- [x] 7.1 Write tests/test_web_search.py (4 test cases)
- [x] 7.2 Verify backend health endpoint works with MCP lifecycle
- [x] 7.3 Test full agent pipeline with web search enabled (SSE events verified)
- [x] 7.4 Test Zilliz Cloud connection, indexing, and search
- [x] 7.5 Test connection test endpoints (LLM, Embedding, Milvus)
