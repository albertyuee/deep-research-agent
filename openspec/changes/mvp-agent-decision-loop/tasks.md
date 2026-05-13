## 1. 项目骨架搭建

- [x] 1.1 创建 Python 项目结构（research_agent/, backend/, frontend/, config/, tests/）
- [x] 1.2 配置 pyproject.toml（依赖：langgraph, fastapi, pymilvus, sentence-transformers, streamlit, openai, sse-starlette, pydantic）
- [x] 1.3 创建 config/settings.py（LLM Provider、Embedding 模型、Milvus 连接、检索参数）
- [x] 1.4 创建 config/.env.example（API keys、数据库连接字符串）

## 2. LLM 多 Provider 封装

- [x] 2.1 实现 research_agent/llm/base.py — BaseLLMClient 抽象接口（chat, stream_chat）
- [x] 2.2 实现 research_agent/llm/qwen_client.py — 通义千问适配
- [x] 2.3 实现 research_agent/llm/openai_client.py — OpenAI 兼容接口适配
- [x] 2.4 实现 research_agent/llm/factory.py — LLM Factory 根据配置创建客户端

## 3. Query Decomposition（查询拆解）

- [x] 3.1 实现 research_agent/planner/decomposer.py — LLM 拆解复杂问题为子问题列表
- [x] 3.2 实现 research_agent/planner/research_plan.py — 生成结构化研究计划（每步含建议检索策略）
- [x] 3.3 实现 LangGraph 节点 `decomposition_node`，读取 query，写入 sub_queries 和 research_plan 到 state
- [x] 3.4 SSE 事件：`research_plan_start` / `research_plan_chunk`

## 4. Adaptive Retrieval（自适应检索）

- [x] 4.1 实现 research_agent/retrieval/embedding.py — BGE-large-v2 Embedding 封装
- [x] 4.2 实现 research_agent/retrieval/vector_store.py — Milvus/Chroma 向量存储与相似度检索
- [x] 4.3 实现 research_agent/retrieval/bm25.py — BM25 关键词检索
- [x] 4.4 实现 research_agent/retrieval/hybrid.py — 混合检索 + RRF 融合
- [x] 4.5 实现 research_agent/retrieval/strategy.py — Agent 自主选择检索策略（semantic/keyword/hybrid）
- [x] 4.6 实现 research_agent/retrieval/rewriter.py — 查询改写（扩展/收缩/切换策略）
- [x] 4.7 实现 LangGraph 节点 `retrieval_node`，根据 strategy 检索，结果写入 state
- [x] 4.8 SSE 事件：`retrieval_start` / `retrieval_result`

## 5. Quality Critique（质量评估）

- [x] 5.1 实现 research_agent/critique/scorer.py — 多维度评分（相关性 0-1 + 完整性 0-1 → 综合分）
- [x] 5.2 实现 research_agent/critique/retry_controller.py — 重试控制（最多 3 次，逐次调整策略）
- [x] 5.3 实现 LangGraph 节点 `critique_node`，评分写入 state，返回 pass/fail 决策
- [x] 5.4 实现条件边 `should_retry`：pass → synthesis，fail + retry_count < 3 → retrieval，fail + retry_count ≥ 3 → synthesis（带低置信度标记）
- [x] 5.5 SSE 事件：`critique_start` / `critique_result` / `retry_triggered`

## 6. Report Synthesis（报告合成）

- [x] 6.1 实现 research_agent/synthesis/aggregator.py — 多源结果去重聚合 + 冲突检测
- [x] 6.2 实现 research_agent/synthesis/report_generator.py — LLM 生成结构化报告（摘要 + 详细发现 + 参考资料）
- [x] 6.3 实现 research_agent/synthesis/citation.py — 内联引用标注 `[来源: doc, chunk, score]`
- [x] 6.4 实现 LangGraph 节点 `synthesis_node`，聚合所有子问题结果生成最终报告
- [x] 6.5 SSE 事件：`synthesis_start` / `synthesis_chunk`

## 7. LangGraph Agent 编排

- [x] 7.1 实现 research_agent/graph.py — StateGraph 定义（4 节点 + 条件边 + 状态类型）
- [x] 7.2 实现 research_agent/state.py — ResearchState TypedDict 定义
- [x] 7.3 实现 research_agent/streaming.py — SSE 事件管理器（节点间事件推送）
- [x] 7.4 Agent 状态流转集成测试（test_graph.py 覆盖全部条件路由分支）

## 8. FastAPI 后端

- [x] 8.1 实现 backend/main.py — FastAPI 应用入口 + CORS
- [x] 8.2 实现 backend/routers/research.py — POST /research（提交任务）、GET /research/{id}/stream（SSE 订阅）
- [x] 8.3 实现 backend/services/research_service.py — 任务管理（创建/查询/状态跟踪）
- [x] 8.4 SSE 流式端点，连接 Agent streaming 到 HTTP 响应（集成于 router + EventBus）

## 9. Streamlit 前端

- [x] 9.1 实现 frontend/app.py — Streamlit 主页面（标题、输入框、提交按钮）
- [x] 9.2 实现 frontend/components/agent_progress.py — 实时展示 Agent 决策过程（拆解 / 检索 / 评估 / 合成步骤可视化）
- [x] 9.3 实现 frontend/components/report_view.py — 最终报告 Markdown 渲染 + 引用溯源列表
- [x] 9.4 实现 frontend/sse_client.py — SSE 客户端，连接后端流式接口

## 10. 文档与测试数据

- [x] 10.1 编写 data/sample_docs/ 示例文档集（3-5 篇 Markdown，覆盖 AI/医疗/金融领域）
- [x] 10.2 编写 tests/test_decomposition.py — 查询拆解单元测试
- [x] 10.3 编写 tests/test_retrieval.py — 检索 + 混合检索单元测试
- [x] 10.4 编写 tests/test_critique.py — 质量评估 + 重试控制单元测试
- [x] 10.5 编写 tests/test_graph.py — Agent 状态流转集成测试
- [x] 10.6 编写 README.md — 项目介绍、架构图、快速开始、技术栈说明
