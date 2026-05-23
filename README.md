# Deep Research Agent

> **Agentic RAG 驱动的深度研究 Agent** — Agent 自主拆解问题、选择检索策略、评估质量、自我纠正，最终生成带引用溯源的结构化研究报告。

[Python](https://python.org)  
[LangGraph](https://langchain.com/langgraph)
[FastAPI](https://fastapi.tiangolo.com)
[Vue 3](https://vuejs.org) + [Vite](https://vitejs.dev) + [Naive UI](https://naiveui.com)
[License](LICENSE)

---

## 核心理念

传统 RAG 是被动式的：**用户问 → 检索 → 回答**。Agent 不会自己判断检索结果质量够不够、搜索方向对不对。

**Deep Research Agent** 让 Agent 具备主动研究能力：

```
用户问题
  → 🔍 自主拆解为 2-5 个子问题
  → 🧠 为每个子问题选择最优检索策略（semantic / keyword / hybrid）
  → 🔎 向量/BM25/RRF 粗排，可选 Rerank 二阶段精排
  → 🧪 检索后自评质量（相关性 + 完整性双维度评分）
  → 🔄 不够好就改写查询重新搜索（最多 3 次，策略逐级升级）
  → 📝 聚合多源信息，生成带引用的结构化报告
```

### 与朴素 RAG 的关键区别


|      | 朴素 RAG | Deep Research Agent                |
| ---- | ------ | ---------------------------------- |
| 检索次数 | 1 次    | 最多 3 次（自适应重试）                      |
| 检索策略 | 固定向量检索 | Agent 自主选择 semantic/keyword/hybrid |
| 质量判断 | 无      | 双维度 LLM Critique                   |
| 查询改写 | 无      | 逐级升级（broaden → switch → rephrase）  |
| 输出   | 单次回答   | 结构化报告 + 内联引用                       |


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
│   └──────────────┘     │ · RRF/Rerank精排  │   │         │
│                        │ · 查询改写        │   │         │
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
│                  SSE Events ────▶ Vue 3 Frontend        │
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


| 层             | 技术                               | 说明                    |
| ------------- | -------------------------------- | --------------------- |
| **Agent 编排**  | LangGraph + StateGraph           | 显式状态流转 + 条件路由         |
| **LLM**       | 硅基流动 / 通义千问 / OpenAI             | 多 Provider 统一封装       |
| **Embedding** | BAAI/bge-large-zh-v1.5（硅基流动 API） | 1024 维向量，支持本地/API 双模式 |
| **向量存储**      | Chroma（默认）/ Milvus               | 持久化 + 余弦相似度           |
| **关键词检索**     | BM25（rank-bm25）+ jieba            | 中文词级分词，互补语义检索      |
| **混合检索**      | RRF 融合                           | 向量 + BM25 结果重排序       |
| **二阶段精排**    | SiliconFlow Rerank                 | 可选 Qwen/Qwen3-Reranker-8B |
| **后端**        | FastAPI + SSE                    | 异步 + 流式推送             |
| **前端**        | Vue 3 + Vite + Naive UI         | Agent 思考过程实时可视化       |
| **配置**        | pydantic-settings + .env         | 类型安全的环境变量管理           |


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

修改 `.env` 文件中的配置：

```env
# LLM 配置
LLM_PROVIDER=siliconflow
LLM_MODEL=Qwen/Qwen3-8B
LLM_API_KEY=sk-your-siliconflow-api-key-here  # 替换为你的真实 key
LLM_BASE_URL=https://api.siliconflow.cn/v1

# Embedding 配置（支持本地/API双模式）
EMBEDDING_MODE=api  # local=本地模型，api=调用API
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
EMBEDDING_API_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_API_KEY=sk-your-siliconflow-api-key-here  # 与 LLM 可共用同一个 key

# Rerank 二阶段精排（可选，默认关闭以避免额外费用）
RERANK_ENABLED=false
RERANK_MODEL=Qwen/Qwen3-Reranker-8B
RERANK_BASE_URL=https://api.siliconflow.cn/v1
# RERANK_API_KEY 留空时复用 LLM_API_KEY，其次复用 EMBEDDING_API_KEY
RERANK_API_KEY=
RERANK_TOP_N=5
RERANK_CANDIDATE_MULTIPLIER=4
```

> **Embedding 模式说明**：
>
> - `EMBEDDING_MODE=local`：使用本地 sentence-transformers 模型，需要预先下载
> - `EMBEDDING_MODE=api`：调用硅基流动 API，无需本地模型，推荐网络条件好时使用

> **如何获取硅基流动 API Key？**
>
> 1. 访问 [cloud.siliconflow.cn](https://cloud.siliconflow.cn) 注册
> 2. 进入控制台 → API 密钥 → 新建密钥
> 3. 新用户赠送 2000 万 token，LLM、Embedding 和 Rerank 可共用同一个 Key

### 4. 索引文档

示例文档（`data/sample_docs/` 下的 Markdown 文件）会在首次启动时自动索引。也可以通过 Web UI 上传自己的文档：

**方式一：Web UI（推荐）**

启动后访问 `http://localhost:5173/documents`，上传 PDF / Word / Markdown / TXT 文件，自动分块、嵌入、索引，立即可被检索。上传接口默认限制单文件最大 `20 MB`，并会对文件名做安全清理，避免路径穿越和特殊字符导致的保存问题。

**方式二：手动索引**

```bash
python3 -c "
from research_agent.retrieval.document_loader import DocumentLoader
from research_agent.retrieval.vector_store import VectorStore
from research_agent.retrieval.bm25 import BM25Retriever

loader = DocumentLoader()
chunks = loader.load_directory('data/sample_docs')

vs = VectorStore()
vs.add_documents(
    [c.chunk_id for c in chunks],
    [c.content for c in chunks],
    [c.metadata for c in chunks],
)
print(f'向量库索引完成: {vs.count} 个 chunk')

bm25 = BM25Retriever()
bm25.index_documents(
    [c.chunk_id for c in chunks],
    [c.content for c in chunks],
    [c.metadata for c in chunks],
)
print(f'BM25 索引完成: {len(chunks)} 条')
"
```

### 5. 一键启动

```bash
./start.sh
```

这会自动：

1. 检查 Python 版本和依赖
2. 检查 ChromaDB 索引状态（已有数据则跳过）
3. 安装前端依赖（首次运行）
4. 启动后端（端口 8000）
5. 启动前端（端口 5173）
6. 打开浏览器访问

也可以手动分步启动：

```bash
# 终端1: 启动后端
uvicorn backend.main:app --reload --port 8000

# 终端2: 启动前端
cd frontend-vue && npm run dev
```

访问 [http://localhost:8000/health](http://localhost:8000/health) 确认后端正常运行。
API 文档：[http://localhost:8000/docs](http://localhost:8000/docs)
前端界面：[http://localhost:5173](http://localhost:5173)

### 6. 开始使用

**深度研究**：输入复杂问题，Agent 自动拆解→检索→评估→合成报告。适合需要深入分析的话题。

**快速检索**：即时问答，AI 摘要 + 来源引用，秒级响应。适合快速查找和简单问题。

**资料管理**：上传 PDF/Word/Markdown/TXT 文档，自动索引入知识库，单文件默认最大 `20 MB`。

**系统设置**：配置 LLM 提供商、嵌入模型、检索参数、Rerank 精排和 Web Search，支持热重载。

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
│   │   ├── embedding.py          # Embedding 服务（支持本地/API双模式）
│   │   ├── vector_store.py       # Chroma 向量存储与检索
│   │   ├── bm25.py               # BM25 关键词检索（jieba 中文分词）
│   │   ├── hybrid.py             # 混合检索 + RRF 融合 + 可选 Rerank
│   │   ├── reranker.py           # SiliconFlow Rerank 二阶段精排
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
│   ├── routers/
│   │   ├── research.py           # 深度研究 API (POST + SSE stream)
│   │   ├── quick_search.py       # 快速检索 API (即时问答)
│   │   ├── documents.py          # 资料管理 API (上传/列表/删除)
│   │   └── settings.py           # 系统设置 API (读/写/热重载)
│   └── services/research_service.py  # 任务管理
├── frontend-vue/                 # Vue 3 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ResearchPage.vue  # 深度研究主页
│   │   │   ├── QuickSearchPage.vue  # 快速检索（对话式）
│   │   │   ├── DocumentsPage.vue # 资料管理（上传/预览/删除）
│   │   │   └── SettingsPage.vue  # 系统设置（LLM/嵌入/检索/Rerank配置）
│   │   ├── components/           # UI 组件
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── composables/          # SSE 连接管理等
│   │   └── api/                  # 后端 API 调用层
│   └── package.json
├── config/                       # 配置
│   ├── settings.py               # pydantic-settings 配置类
│   ├── .env                      # 实际配置（不提交 Git）
│   └── .env.example              # 配置模板
├── data/
│   ├── sample_docs/              # 示例文档
│   │   ├── ai_medical_imaging.md
│   │   ├── ai_drug_discovery.md
│   │   └── rag_technology_overview.md
│   ├── chroma_db/                # ChromaDB 持久化数据
│   └── uploads/                  # 用户上传的文件
├── tests/                        # 测试（29 个用例）
│   ├── test_decomposition.py     # 查询拆解
│   ├── test_retrieval.py         # 检索模块（BM25/jieba/Rerank）
│   ├── test_critique.py          # 质量评估 + 重试控制
│   ├── test_web_search.py        # MCP Web Search 归一化
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


| Event                 | 数据                                            | 说明     |
| --------------------- | --------------------------------------------- | ------ |
| `research_plan_start` | `{query}`                                     | 开始拆解问题 |
| `research_plan_chunk` | `{index, question, strategy}`                 | 每个子问题  |
| `retrieval_start`     | `{step, total, strategy}`                     | 开始检索   |
| `retrieval_result`    | `{result_count, top_score}`                   | 检索完成   |
| `critique_start`      | `{step}`                                      | 开始评估质量 |
| `critique_result`     | `{composite_score, passed, retry_suggestion}` | 评估结果   |
| `retry_triggered`     | `{step, count}`                               | 触发重试   |
| `synthesis_start`     | `{}`                                          | 开始合成报告 |
| `synthesis_chunk`     | `{text}`                                      | 报告文本片段 |
| `done`                | `{}`                                          | 完成     |


### POST /api/v1/quick-search

快速检索 + AI 摘要（同步，秒级响应）。

```bash
curl -X POST http://localhost:8000/api/v1/quick-search \
  -H "Content-Type: application/json" \
  -d '{"query": "Transformer的核心机制是什么？", "top_k": 5}'
```

**Response:** `{ success, data: { query, summary, sources[], elapsed_ms } }`

### Documents API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/documents` | 文件列表（含 ChromaDB 已索引文档） |
| POST | `/api/v1/documents/upload` | 上传文档（multipart），默认最大 20MB，安全文件名处理，自动分块+嵌入+索引 |
| DELETE | `/api/v1/documents/{id}` | 删除文档及所有关联 chunks |

支持 PDF/DOCX/MD/TXT，上传后立即可被深度研究和快速检索使用。文件保存时会清理路径分隔符、控制字符和异常符号，防止用户上传文件名影响服务器路径。

### Settings API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/settings` | 读取当前配置（API Key 掩码） |
| PATCH | `/api/v1/settings` | 部分更新配置，写 .env 并热重载（含 LLM/Embedding/Retrieval/Rerank/MCP） |
| GET | `/api/v1/settings/system-info` | ChromaDB 统计 + 版本信息 |

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

## 当前增强能力

- **中文关键词检索**：BM25 已接入 `jieba` 中文词级分词，提升中文关键词匹配效果。
- **Rerank 二阶段精排**：支持硅基流动 `Qwen/Qwen3-Reranker-8B`，默认关闭；开启后先召回候选结果，再按相关性精排。
- **上传安全**：文档上传默认限制 `20 MB`，并清理上传文件名，避免路径穿越和特殊字符导致的保存问题。

## 后续规划

- **V2**：Knowledge Graph 构建 + 多跳推理（NetworkX → Neo4j）
- **V3**：MCP 多源接入（Notion, GitHub, 数据库）
- **V4**：Agent 记忆系统（短期对话 + 长期用户画像）+ 多轮对话
- **V5**：RAGAS 评估看板 + LangFuse 全链路追踪

---

## 运行测试

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q
# 29 passed
```

前端构建检查：

```bash
cd frontend-vue && npm run build
```

真实接口连通性已验证：LLM、Embedding API、SiliconFlow `Qwen/Qwen3-Reranker-8B` Rerank 均可正常调用。

---

## License

MIT © 2025 Liu Yue

---

**GitHub**: [github.com/956501819](https://github.com/956501819) | **相关项目**: [sql-agent-kit](https://github.com/956501819/sql-agent-kit)