# Deep Research Agent

> **Agentic RAG 驱动的深度研究 Agent** — Agent 自主拆解问题、选择检索策略、评估质量、自我纠正，最终生成带引用溯源的结构化研究报告。

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![LangGraph](https://img.shields.io/badge/Agent-LangGraph-orange)](https://langchain.com/langgraph)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-green)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

与 [sql-agent-kit](https://github.com/956501819/sql-agent-kit)（结构化数据 Text-to-SQL 多 Agent 工具包）互补，覆盖 **AI Agent 开发面试**中「结构化 + 非结构化」两大核心场景。

---

## 核心理念

传统 RAG 是被动式的：**用户问 → 检索 → 回答**。Agent 不会自己判断检索结果质量够不够、搜索方向对不对。

**Deep Research Agent** 让 Agent 具备主动研究能力：

```
用户问题
  → 🔍 自主拆解为 2-5 个子问题
  → 🧠 为每个子问题选择最优检索策略（semantic / keyword / hybrid）
  → 🔎 检索后自评质量（相关性 + 完整性双维度评分）
  → 🔄 不够好就改写查询重新搜索（最多 3 次，策略逐级升级）
  → 📝 聚合多源信息，生成带引用的结构化报告
```

### 与朴素 RAG 的关键区别

| | 朴素 RAG | Deep Research Agent |
|---|---|---|
| 检索次数 | 1 次 | 最多 3 次（自适应重试） |
| 检索策略 | 固定向量检索 | Agent 自主选择 semantic/keyword/hybrid |
| 质量判断 | 无 | 双维度 LLM Critique |
| 查询改写 | 无 | 逐级升级（broaden → switch → rephrase） |
| 输出 | 单次回答 | 结构化报告 + 内联引用 |

---

## Agent 架构

```
┌─────────────────────────────────────────────────────────┐
│                    LangGraph Agent                       │
│                                                          │
│   用户问题                                                │
│      │                                                   │
│      ▼                                                   │
│   ┌──────────────┐     ┌─────────────────┐              │
│   │ Decomposition│────▶│   Retrieval      │◀──┐         │
│   │    Node      │     │     Node         │   │         │
│   │              │     │                  │   │ 重试     │
│   │ · 拆解子问题  │     │ · 策略选择        │   │ (最多3次) │
│   │ · 生成研究计划│     │ · 向量/BM25/混合  │   │         │
│   └──────────────┘     │ · 查询改写        │   │         │
│                        └────────┬────────┘   │         │
│                                 │            │         │
│                                 ▼            │         │
│                        ┌──────────────┐     │         │
│                        │   Critique   │─────┘         │
│                        │     Node     │               │
│                        │              │               │
│                        │ · 相关性评分   │               │
│                        │ · 完整性评分   │               │
│                        │ · 重试建议     │               │
│                        └──────┬───────┘               │
│                               │ 通过 / 重试耗尽        │
│                               ▼                        │
│                        ┌──────────────┐               │
│                        │  Synthesis   │               │
│                        │    Node      │               │
│                        │              │               │
│                        │ · 多源聚合    │               │
│                        │ · 冲突检测    │               │
│                        │ · 报告生成    │               │
│                        │ · 引用标注    │               │
│                        └──────────────┘               │
│                                 │                      │
│                  SSE Events ────▶ Streamlit Frontend    │
└─────────────────────────────────────────────────────────┘
```

### Agent 状态流转

```
Decomposition → Retrieval → Critique → should_retry?
                                           │
                    ┌──────────────────────┤
                    ▼                      ▼
              pass / more steps      fail + can retry
                    │                      │
                    ▼                      ▼
              next step              back to Retrieval
                    │                (query rewritten,
                    ▼                 strategy adjusted)
              all done?
                    │
                    ▼
               Synthesis → END
```

---

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| **Agent 编排** | LangGraph + StateGraph | 显式状态流转 + 条件路由 |
| **LLM** | 硅基流动 / 通义千问 / OpenAI | 多 Provider 统一封装 |
| **Embedding** | BAAI/bge-large-zh-v1.5 | 1024 维向量 |
| **向量存储** | Chroma（默认）/ Milvus | 持久化 + 余弦相似度 |
| **关键词检索** | BM25（rank-bm25） | 互补语义检索 |
| **混合检索** | RRF 融合 | 向量 + BM25 结果重排序 |
| **后端** | FastAPI + SSE | 异步 + 流式推送 |
| **前端** | Streamlit | Agent 思考过程实时可视化 |
| **配置** | pydantic-settings + .env | 类型安全的环境变量管理 |

---

## 快速开始

### 前提条件

- Python 3.12+
- 硅基流动 API Key（[免费注册](https://cloud.siliconflow.cn)，新用户赠送 2000 万 token）

其他可用的 LLM Provider：
- 阿里云百炼：[https://dashscope.aliyun.com](https://dashscope.aliyun.com)
- OpenAI：[https://platform.openai.com](https://platform.openai.com)

### 1. 克隆项目

```bash
git clone https://github.com/956501819/deep-research-agent.git
cd deep-research-agent
```

### 2. 安装依赖

```bash
pip install -e ".[dev]"
```

### 3. 配置 API Key

```bash
# 编辑 .env 文件，填入你的硅基流动 API Key
vim config/.env
```

修改这一行：
```env
LLM_API_KEY=sk-your-siliconflow-api-key-here  # 替换为你的真实 key
```

> **如何获取硅基流动 API Key？**
> 1. 访问 [cloud.siliconflow.cn](https://cloud.siliconflow.cn) 注册
> 2. 进入控制台 → API 密钥 → 新建密钥
> 3. 新用户赠送 2000 万 token，足够开发测试使用

### 4. 索引示例文档

```bash
python -c "
from research_agent.retrieval.vector_store import VectorStore
from research_agent.retrieval.bm25 import BM25Retriever
from pathlib import Path

# 加载示例文档
data_dir = Path('data/sample_docs')
docs = []
for f in data_dir.glob('*.md'):
    with open(f) as fp:
        docs.append((f.stem, fp.read(), {'doc_title': f.stem, 'source': f.name}))

ids = [d[0] for d in docs]
texts = [d[1] for d in docs]
metadatas = [d[2] for d in docs]

# 分块（简单按段落切分）
chunks = []
chunk_ids = []
chunk_metas = []
for i, text in enumerate(texts):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    for j, para in enumerate(paragraphs):
        if len(para) > 50:
            chunks.append(para)
            chunk_ids.append(f'{ids[i]}_chunk_{j}')
            chunk_metas.append({**metadatas[i], 'chunk_index': j})

# 索引到向量库
vs = VectorStore()
vs.add_documents(chunk_ids, chunks, chunk_metas)
print(f'向量库索引完成: {vs.count} 个 chunk')

# 索引到 BM25
bm25 = BM25Retriever()
bm25.index_documents(chunk_ids, chunks, chunk_metas)
print(f'BM25 索引完成: {len(chunks)} 条')
"
```

### 5. 启动后端

```bash
uvicorn backend.main:app --reload
```

访问 [http://localhost:8000/health](http://localhost:8000/health) 确认后端正常运行。

API 文档：[http://localhost:8000/docs](http://localhost:8000/docs)

### 6. 启动前端

在另一个终端：

```bash
streamlit run frontend/app.py
```

浏览器会自动打开 Streamlit 界面。

### 7. 开始研究

在输入框中输入你的研究问题，例如：

> **"人工智能在医疗影像和药物研发中的应用有什么区别？"**

Agent 会自动完成：拆解子问题 → 检索 → 评估质量 → 生成对比分析报告。

更多示例问题：

- "RAG 技术从 2023 到 2026 年经历了哪些演进阶段？"
- "联邦学习在医疗 AI 中有哪些实际部署案例？"
- "AlphaFold 是如何改变药物研发流程的？"

---

## 项目结构

```
deep-research-agent/
├── research_agent/               # 核心 Agent 逻辑
│   ├── llm/                      # LLM 多 Provider 封装
│   │   ├── base.py               # BaseLLMClient 抽象接口
│   │   ├── qwen_client.py        # 通义千问适配
│   │   ├── openai_client.py      # OpenAI 兼容接口适配
│   │   └── factory.py            # LLM Factory（自动选择 Provider）
│   ├── planner/                  # 查询拆解 + 研究计划
│   │   ├── decomposer.py         # LLM 拆解复杂问题为子问题
│   │   └── research_plan.py      # 结构化研究计划
│   ├── retrieval/                # 自适应检索
│   │   ├── embedding.py          # BGE-large-v2 Embedding
│   │   ├── vector_store.py       # Chroma 向量存储与检索
│   │   ├── bm25.py               # BM25 关键词检索
│   │   ├── hybrid.py             # 混合检索 + RRF 融合
│   │   ├── strategy.py           # Agent 自主选择检索策略
│   │   └── rewriter.py           # 查询改写（扩展/收缩/切换）
│   ├── critique/                 # 检索质量评估
│   │   ├── scorer.py             # 双维度评分（相关性 + 完整性）
│   │   └── retry_controller.py   # 重试控制（最多 3 次，策略升级）
│   ├── synthesis/                # 报告合成
│   │   ├── aggregator.py         # 多源结果去重聚合 + 冲突检测
│   │   ├── report_generator.py   # LLM 生成结构化报告
│   │   └── citation.py           # 内联引用标注 + 参考资料列表
│   ├── state.py                  # Agent 状态定义（ResearchState TypedDict）
│   ├── streaming.py              # SSE 事件总线（EventBus）
│   └── graph.py                  # LangGraph Agent 编排（4 节点 + 条件路由）
├── backend/                      # FastAPI 后端
│   ├── main.py                   # 应用入口 + CORS + 生命周期
│   ├── routers/research.py       # POST /research, GET /research/{id}/stream
│   └── services/research_service.py  # 任务管理
├── frontend/                     # Streamlit 前端
│   ├── app.py                    # 主页面（输入框 + 提交 + 结果展示）
│   ├── sse_client.py             # SSE 客户端
│   └── components/
│       ├── agent_progress.py     # Agent 思考过程实时可视化
│       └── report_view.py        # 报告渲染 + 引用列表
├── config/                       # 配置
│   ├── settings.py               # pydantic-settings 配置类
│   ├── .env                      # 实际配置（不提交 Git）
│   └── .env.example              # 配置模板
├── data/sample_docs/             # 示例文档
│   ├── ai_medical_imaging.md     # AI 医疗影像
│   ├── ai_drug_discovery.md      # AI 药物研发
│   └── rag_technology_overview.md # RAG 技术概述
├── tests/                        # 测试（26 个用例）
│   ├── test_decomposition.py     # 查询拆解
│   ├── test_retrieval.py         # 检索模块
│   ├── test_critique.py          # 质量评估 + 重试控制
│   └── test_graph.py             # Agent 状态流转集成测试
├── openspec/                     # OpenSpec 规范驱动开发
│   ├── project.md                # 项目上下文
│   ├── specs/                    # 已有 specs
│   └── changes/                  # 变更记录
├── pyproject.toml                # 项目元信息 + 依赖
└── README.md
```

---

## API 文档

### POST /api/v1/research

提交研究任务。

```bash
curl -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "RAG技术的演进阶段有哪些？"}'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "task_id": "a1b2c3d4e5f6"
  }
}
```

### GET /api/v1/research/{task_id}/stream

SSE 流式订阅 Agent 执行进度。

```bash
curl -N http://localhost:8000/api/v1/research/a1b2c3d4e5f6/stream
```

**SSE Events:**

| Event | 数据 | 说明 |
|-------|------|------|
| `research_plan_start` | `{query}` | 开始拆解问题 |
| `research_plan_chunk` | `{index, question, strategy}` | 每个子问题 |
| `retrieval_start` | `{step, total, strategy}` | 开始检索 |
| `retrieval_result` | `{result_count, top_score}` | 检索完成 |
| `critique_start` | `{step}` | 开始评估质量 |
| `critique_result` | `{composite_score, passed, retry_suggestion}` | 评估结果 |
| `retry_triggered` | `{step, count}` | 触发重试 |
| `synthesis_start` | `{}` | 开始合成报告 |
| `synthesis_chunk` | `{text}` | 报告文本片段 |
| `done` | `{}` | 完成 |

### GET /api/v1/research/{task_id}

查询任务状态和结果。

```json
{
  "success": true,
  "data": {
    "task_id": "a1b2c3d4e5f6",
    "query": "RAG技术的演进阶段有哪些？",
    "status": "completed",
    "result": {
      "report": "...markdown报告...",
      "sub_queries": [...],
      "sources_count": 12
    }
  }
}
```

---

## 面试展示要点

这个项目涵盖 **AI Agent 开发面试 85% 以上的高频考点**：

### Agent 架构
- **LangGraph StateGraph**：显式状态 + 条件路由，不是黑盒 AgentExecutor
- **ReAct 推理链路**：Plan → Execute → Evaluate → Retry
- **自我纠错**：3 级逐步升级重试（broaden → switch strategy → rephrase）

### RAG 深度
- **自适应检索策略**：Agent 根据查询特征自主选择 semantic / keyword / hybrid
- **混合检索**：稠密向量 + 稀疏 BM25 + RRF 融合
- **质量 Critique**：相关性 + 完整性双维度 LLM 评分
- **查询改写**：检索失败时自动改写查询（扩展/收缩/切换）

### 工程能力
- **SSE 流式推送**：Agent 思考过程实时可见
- **多 Provider 封装**：硅基流动 / 通义千问 / OpenAI 统一接口
- **模块化设计**：每个节点独立可插拔
- **26 个单元测试**：覆盖核心逻辑 + 状态流转
- **OpenSpec 规范驱动开发**：proposal → design → specs → tasks → implement

### 可在面试中展开讨论的点

| 面试问题 | 项目中的答案 |
|---------|------------|
| 为什么用混合检索而不是纯向量？ | 概念查询用语义，实体/数字查询用关键词，RRF 融合互补 |
| 如何控制 Agent 幻觉？ | 3 层控制：检索质量阈值拒答 + Prompt 上下文约束 + 低置信度标记 |
| Critique 为什么是独立节点？ | 职责分离，可插拔替换为 Cross-Encoder / 规则引擎 |
| 如何处理检索失败？ | 3 级升级策略 + 最终降级到"最佳可用结果 + 低置信度标记" |
| SSE vs WebSocket 为什么选 SSE？ | 单向推送够用，协议更轻，与 sql-agent-kit 保持一致 |
| 如何扩展新数据源？ | MCP 协议（V2 规划），新增数据源不改 Agent 核心逻辑 |

---

## 与 sql-agent-kit 的关系

| | sql-agent-kit | Deep Research Agent |
|---|---|---|
| **定位** | 结构化数据查询 | 非结构化文档研究 |
| **数据形态** | 数据库表（MySQL/PostgreSQL/Hive） | 文档/网页（PDF/Word/Markdown） |
| **Agent 模式** | Planner → SQL → Chart → Judge 流水线 | 拆解 → 检索 → 评估 → 重试 → 合成 |
| **核心技术** | Text-to-SQL + 多 Agent 协作 | Agentic RAG + 自我纠错 |
| **输出** | SQL 查询 + 图表 + 分析结论 | 结构化研究报告 + 引用溯源 |
| **Agent 框架** | LangGraph | LangGraph |
| **前端** | Vue 3 | Streamlit |
| **MCP** | 数据库查询（MySQL/Hive） | 多源异构数据接入（V2 规划中） |

两个项目共享相同的技术栈基础（LangGraph / 多 Provider LLM / SSE / FastAPI），分别覆盖 Agent 面试的「结构化数据」和「非结构化数据」两大场景，形成完整的 Agent 开发能力展示。

---

## 后续规划

- **V2**：Knowledge Graph 构建 + 多跳推理（NetworkX → Neo4j）
- **V3**：MCP 多源接入（Web Search, Notion, GitHub, 数据库）
- **V4**：Agent 记忆系统（短期对话 + 长期用户画像）
- **V5**：RAGAS 评估看板 + LangFuse 全链路追踪

---

## 运行测试

```bash
pytest tests/ -v
# 26 passed
```

---

## License

MIT © 2025 Liu Yue

---

**GitHub**: [github.com/956501819](https://github.com/956501819) | **相关项目**: [sql-agent-kit](https://github.com/956501819/sql-agent-kit)
