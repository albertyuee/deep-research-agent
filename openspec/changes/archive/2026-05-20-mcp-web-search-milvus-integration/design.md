## Context

Deep Research Agent 原本使用 ChromaDB 嵌入式向量存储 + 纯本地检索。升级 anyio 到 4.x（MCP SDK 要求）后，ChromaDB 1.5.9 内嵌 HTTP 服务器与 anyio 4.x 不兼容，间歇性 `Connection reset by peer` 崩溃。同时需要接入外部搜索能力以获取实时信息。

## Goals / Non-Goals

**Goals:**
- 通过 MCP 协议接入 Tavily Web Search，Agent 自主判断何时联网
- 新增 Zilliz Cloud / 自建 Milvus 向量存储后端，彻底解决 ChromaDB 兼容问题
- 前端设置页面支持切换向量存储后端、配置 Zilliz 凭证、测试连接
- ChromaDB 崩溃时自动降级，不中断 Agent 执行

**Non-Goals:**
- 不接入 Web Search 以外的 MCP 工具（如 GitHub、Notion 等 V3 规划）
- 不重构整个向量存储抽象层
- 不需要同时支持多个向量后端热切换

## Decisions

### 1. MCP Server 自建而非用第三方 npm 包
**选型**: 自建 Python MCP Server (`mcp_servers/web_search/server.py`)，通过 stdio 与主进程通信。
**理由**: 纯 Python 依赖，无 Node.js 环境要求；完全可控的 Tavily API 调用；适合面试展示。
**备选**: `tavily-mcp` (npm) — 需要 Node.js；`@anthropic/mcp-server-brave-search` — 同上。

### 2. Web Search 集成点：检索节点内部路由而非独立节点
**选型**: 在 `retrieval_node` 内根据 `data_source` 字段分发，而非新增 LangGraph 节点。
**理由**: 最小改动；共享 critique/retry 逻辑；结果格式统一。
**备选**: 独立的 `web_search` 节点 — 需要重构整个图结构和条件路由。

### 3. 数据源决策权交给 LLM Decomposer
**选型**: Decomposer 为每个子问题标记 `data_source: local | web | both`。
**开关控制**: 前端 `enable_web_search` 开关 + API Key 双重校验。
**开关关闭时**: Decomposer 只建议 `local`，web search 完全不触发。

### 4. Zilliz Cloud 支持：自动检测 Embedding 维度
**选型**: `_ensure_collection()` 调用 `get_embedding_service().dimension` 自动获取实际维度（1024）。
**理由**: 避免配置写死导致维度不匹配；支持切换 embedding 模型。
**备选**: 配置写死 — 切换模型时需要手动改配置，易出错。

### 5. ChromaDB 降级策略：try/except + web fallback
**选型**: `retrieval_node` 中 try/except 包裹本地检索。`data_source="both"` 时崩溃则用 web 结果顶上；`data_source="local"` 则 re-raise 触发重试。

## Risks / Trade-offs

- [Web Search 会增加延迟] → Tavily API 调用 1-3 秒，但 Agent 整体执行几十秒到几分钟，用户无感知
- [MCP Server 子进程可能崩溃] → `search_web()` 捕获所有异常返回 `[]`，Agent 降级为纯本地检索
- [Milvus 维度写死 384 可能不匹配] → 已在 `_ensure_collection()` 中改为自动检测 embedding dimension
- [切换存储后端时数据为空] → 默认创建空 collection，用户需重新索引文档。UI 已添加 warning 提示
