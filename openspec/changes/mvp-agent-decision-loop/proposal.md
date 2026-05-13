## Why

传统被动式 RAG（用户问 → 检索 → 回答）在面对复杂分析性问题时存在根本局限：Agent 不会自主判断"检索结果质量够不够"、"是否需要换个角度重新搜索"，导致多跳推理失败、信息覆盖不全。本项目要解决的核心问题：**让 Agent 自主决策检索策略、评估检索质量、自我纠正，从"被动检索"升级为"主动研究"**。这是 AI Agent 开发面试中区分"会用 RAG"和"理解 Agentic RAG"的关键分水岭。

## What Changes

- 新增 Query Decomposition（问题拆解）能力：复杂问题自动拆为 2-5 个子问题，生成结构化研究计划
- 新增 Adaptive Retrieval（自适应检索）能力：Agent 自主选择向量检索或 BM25 关键词检索，检索后评估质量，低置信度时自动改写查询重新检索
- 新增 Quality Critique（质量评估）能力：对检索结果做相关性 + 完整性评分，不达标则触发重试（最多 3 次），逐次放宽检索条件
- 新增 Report Synthesis（报告合成）能力：多源结果去重聚合，生成带引用溯源的结构化报告
- 新增 SSE 流式推送：Agent 思考过程（拆解 → 检索 → 评估 → 合成）实时可见
- 新增 FastAPI 后端 + Streamlit 前端：提供 Web 交互界面

## Capabilities

### New Capabilities
- `query-decomposition`: 复杂问题自动拆解为子问题并生成研究计划
- `adaptive-retrieval`: Agent 自主选择检索策略（向量/BM25）、评估质量、改写查询重试
- `quality-critique`: 检索结果相关性 + 完整性评估，控制重试流程（最多 3 次）
- `report-synthesis`: 多源结果聚合去重，生成带引用溯源的结构化报告
- `agent-orchestration`: LangGraph 编排 Agent 决策流（拆解 → 检索 → 评估 → 合成），支持 SSE 流式推送

### Modified Capabilities
<!-- 首个 change，无已有 spec 需要修改 -->

## Impact

- 新增目录：`research_agent/planner/`, `research_agent/retrieval/`, `research_agent/critique/`, `research_agent/synthesis/`
- 新增依赖：LangGraph, Milvus/Chroma, BGE Embedding, FastAPI, Streamlit, LangFuse
- 新增 API 路由：`POST /research`（提交研究任务）、`GET /research/{id}/stream`（SSE 流式订阅）
- 与已有 sql-agent-kit 共享：LLM 多 Provider 封装模式、SSE 流式推送模式、MCP 协议模式（后续版本复用）
