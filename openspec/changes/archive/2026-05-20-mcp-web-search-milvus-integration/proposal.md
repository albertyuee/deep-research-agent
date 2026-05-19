## Why

Deep Research Agent 当前只能检索本地 ChromaDB 索引的文档，无法获取实时信息。且 ChromaDB 1.5.9 与 anyio 4.x 不兼容，导致 50% 概率崩溃。需要接入外部搜索能力和稳定的向量存储后端。

## What Changes

- **MCP Web Search**：通过 MCP 协议接入 Tavily Search API，Agent 自主判断每个子问题是否需要联网搜索，支持前端开关控制
- **Milvus / Zilliz Cloud 向量存储**：新增 MilvusVectorStore，支持 Zilliz Cloud（托管）和自建 Milvus，自动检测 embedding 维度
- **系统设置增强**：向量存储后端选择器（ChromaDB / Milvus），Zilliz Cloud 凭证配置，LLM/Embedding/Milvus 连接测试按钮
- **检索容错**：ChromaDB 崩溃时，若 web search 可用则用 web 结果兜底，不影响 Agent 运行
- **前端实时展示**：WebSearchCard 组件展示抓取的网页 URL 和摘要
- **依赖更新**：anyio 3→4, fastapi/uvicorn/starlette 升级以兼容 MCP SDK 1.27

## Capabilities

### New Capabilities
- `mcp-web-search`: Agent 通过 MCP 协议调用外部搜索工具，支持前端开关和数据源路由
- `milvus-vector-store`: 支持 Zilliz Cloud 和自建 Milvus 作为向量存储后端
- `settings-connection-test`: 系统设置页面提供 LLM/Embedding/向量存储的连接测试功能

### Modified Capabilities
<!-- 无现有 spec 被修改 -->

## Impact

- **新增依赖**: mcp>=1.27.0, httpx>=0.25.0（已在 pyproject.toml）
- **新增模块**: research_agent/tools/, mcp_servers/web_search/
- **修改模块**: research_agent/graph.py, research_agent/retrieval/vector_store.py, backend/routers/settings.py, config/settings.py
- **新增前端组件**: WebSearchCard.vue, SettingsSection.vue（header-extra slot）
- **修改前端页面**: ResearchPage.vue, SettingsPage.vue, SearchForm.vue
