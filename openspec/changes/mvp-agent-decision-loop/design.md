## Context

刘悦在搜狐完成了两个 AI Agent 项目：基于 ReAct 的数据分析 Agent（Text-to-SQL）和基于被动式 RAG 的智能客服系统。智能客服系统的核心局限在于：检索策略是固定的（用户问 → Embedding → Top-K 召回 → 回答），Agent 不具备自主判断检索质量、改写查询、多轮深挖的能力。

本项目将 Agent 决策能力引入 RAG 链路，构建一个能"主动研究"而非"被动检索"的 Deep Research Agent，与已有 sql-agent-kit（结构化数据查询）形成互补，覆盖 Agent 面试中"结构化 + 非结构化"两大数据场景。

技术选型与已有项目保持连续性：LangGraph（已有经验）、Milvus（已有经验）、Qwen（已有经验）、FastAPI + SSE（已有经验）、MCP（后续版本复用）。

## Goals / Non-Goals

**Goals:**
- 实现 LangGraph 编排的 Agent 决策循环：Query Decomposition → Adaptive Retrieval → Quality Critique → Report Synthesis
- Agent 自主评估检索质量并决定是否重试（最多 3 次）
- 支持向量检索 + BM25 混合检索，Agent 自主选择策略
- SSE 流式推送 Agent 思考过程，每步可见
- FastAPI 后端 + Streamlit 前端，可交互演示

**Non-Goals:**
- 知识图谱构建与多跳推理（V2）
- MCP 多源接入（V3）
- 用户认证、多租户、持久化存储
- 生产级部署配置
- Web Search 实时联网检索（后续版本）

## Decisions

### 1. LangGraph StateGraph 编排 Agent 流程

**选择**: LangGraph StateGraph + 条件边 (conditional edges) 实现 Agent 节点路由
**替代**: LangChain AgentExecutor（黑盒，难以展示决策逻辑）
**理由**: LangGraph 显式定义状态流转，面试中可以清晰展示 Agent 决策架构图。与 sql-agent-kit 技术栈一致，降低学习成本。

Agent 状态定义：
```python
class ResearchState(TypedDict):
    query: str                          # 原始问题
    sub_queries: List[str]              # 拆解后的子问题
    research_plan: List[dict]           # 研究计划
    current_step: int                   # 当前步骤
    retrieval_results: List[dict]       # 检索结果
    critique_score: float               # 质量评分
    retry_count: int                    # 重试计数
    final_report: str                   # 最终报告
    sources: List[dict]                 # 引用溯源
```

### 2. 混合检索策略：向量 + BM25 + RRF 融合

**选择**: BGE-large-v2 向量 + BM25 关键词 + Reciprocal Rank Fusion (RRF)
**替代**: 纯向量检索（语义漂移导致精确关键词匹配失败）
**理由**: Agent 根据查询特征选择策略 —— 概念性问题偏向量，术语/数字类问题偏 BM25。RRF 融合两种排序，无需调参。

### 3. Quality Critique 独立节点

**选择**: Critique 作为独立 LangGraph 节点，而非内嵌在 Retrieval 中
**替代**: 在 Retrieval 节点内直接做质量判断
**理由**:
- 职责分离，Critique 可插拔（后续可替换为 Cross-Encoder 评分、规则引擎等）
- 面试中可以清晰展示"评估-决策-重试"的设计模式
- 便于对 Critique 节点单独评估和优化

Critique 维度：
- **相关性** (0-1): 检索结果与子问题的语义匹配度
- **完整性** (0-1): 检索结果是否覆盖了子问题的关键信息点
- **综合评分** = 0.6 × 相关性 + 0.4 × 完整性
- 阈值 < 0.6 触发重试，每次重试调整检索策略（扩大 k 值、切换检索方式、改写查询）

### 4. SSE 流式推送 Agent 思考过程

**选择**: FastAPI + SSE，每个 Agent 节点执行时推送状态事件
**替代**: WebSocket（更重，MVP 不需要双向通信）
**理由**: 与 sql-agent-kit 的 SSE 模式一致，前端实时展示 Agent 思考链路，面试演示效果好。

事件类型：
```
research_plan_start   → 开始拆解问题
research_plan_chunk   → 子问题/计划片段
retrieval_start       → 开始检索
retrieval_result      → 检索结果摘要
critique_start        → 开始评估质量
critique_result       → 评分与决策
retry_triggered       → 触发重试
synthesis_start       → 开始合成报告
synthesis_chunk       → 报告片段
done                  → 完成
```

### 5. Streamlit 作为 MVP 前端

**选择**: Streamlit（纯 Python，快速出 demo）
**替代**: Vue 3（开发周期长，MVP 阶段投入产出比低）
**理由**: 面试演示只需要可交互的 Web 界面，Streamlit 1-2 天即可完成。后续迭代切换到 Vue 3 时，FastAPI 接口层无需改动。

## Risks / Trade-offs

- **[延迟风险] LLM Critique 增加 2-5 秒延迟** → 异步执行 + 流式推送缓解感知延迟；设置 30 秒总超时
- **[准确率风险] LLM 评估检索质量可能不可靠** → Critique Prompt 使用结构化 JSON 输出 + 明确评分标准；后续版本引入 Cross-Encoder 精排评分
- **[成本风险] 重试机制导致 Token 消耗增加** → 最多 3 次重试 + 每次重试减小 Prompt 上下文；语义缓存减少重复查询
- **[冷启动] Embedding 模型对专业领域覆盖面不足** → 支持切换 Embedding 后端（BGE → 领域微调模型）

## Open Questions

- Critique 评分阈值 0.6 是否合理？需上线后用真实数据校准
- 子问题拆解粒度：3 个还是 5 个子问题更优？需实验对比
- 检索 k 值：初始 Top-5，重试时扩展到 Top-10 还是 Top-20？
