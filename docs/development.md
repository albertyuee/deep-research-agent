# 开发指南

本文面向需要本地调试、扩展检索链路或参与前后端开发的贡献者。首次使用项目时先阅读根目录的 [README](../README.md)，权限相关改动同时参考 [权限管理](permissions.md)。

## 1. 环境与安装

推荐环境：

- Python 3.12 或更高版本；
- Node.js 18 或更高版本；
- macOS 或 Linux；
- 至少一个可用的 LLM 与 Embedding 服务，或本地 Embedding 模型。

项目统一使用根目录下的 `.venv`，避免全局 Python 包版本污染：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"

cd frontend-vue
npm install
cd ..
```

复制配置模板，不要将真实密钥提交到 Git：

```bash
cp config/.env.example config/.env
```

## 2. 启动与调试

推荐使用一键启动脚本：

```bash
./start.sh
```

脚本会检查项目虚拟环境、Python 依赖、前端依赖和端口占用，并启动：

| 服务 | 默认地址 |
|---|---|
| Vue 前端 | `http://localhost:5173` |
| FastAPI 后端 | `http://localhost:8000` |
| Swagger | `http://localhost:8000/docs` |
| 健康检查 | `http://localhost:8000/health` |

需要分别查看日志时，可以手动启动：

```bash
# 终端 1
.venv/bin/python -m uvicorn backend.main:app --reload --port 8000

# 终端 2
cd frontend-vue
npm run dev -- --port 5173 --strictPort
```

`AUTH_ENABLED=true` 时，未登录用户会被前端路由守卫送到 `/login`，后端受保护接口也会返回 `401`。

## 3. 目录与模块职责

```text
deep-research-agent/
├── backend/
│   ├── main.py                    # FastAPI 入口、CORS 和路由注册
│   ├── auth.py                    # 登录、RBAC、文档 ACL 策略
│   ├── routers/                   # auth/research/documents/settings 等 API
│   └── services/                  # 研究任务状态与生命周期
├── config/
│   ├── settings.py                # Pydantic Settings 配置模型
│   └── .env.example               # 可提交的环境变量模板
├── frontend-vue/src/
│   ├── api/                       # HTTP、鉴权与业务 API 封装
│   ├── components/                # 可复用界面组件
│   ├── composables/               # SSE 等组合逻辑
│   ├── pages/                     # 页面级组件
│   ├── router/                    # 路由和登录守卫
│   └── stores/                    # Pinia 状态
├── research_agent/
│   ├── planner/                   # 子问题拆解与依赖规划
│   ├── nodes/                     # LangGraph 节点实现
│   │   ├── planning.py            # 规划与研究模式归一化
│   │   ├── retrieval.py           # 本地/联网/混合检索
│   │   ├── critique.py            # 质量评估、重试与步骤推进
│   │   ├── research.py            # 依赖层并发调度
│   │   └── synthesis.py           # 结果聚合与报告生成
│   ├── retrieval/                 # Vector、BM25、RRF、Rerank
│   ├── critique/                  # 相关性/完整性评估与重试
│   ├── reasoning/                 # 多跳 working memory
│   ├── synthesis/                 # 报告与引用生成
│   ├── observability/             # 阶段耗时记录
│   ├── graph.py                   # LangGraph 编排门面
│   ├── state.py                   # Agent 状态定义
│   └── streaming.py               # 内存 SSE 事件总线
├── scripts/                       # 数据导入与评测脚本
├── tests/                         # 后端单元/集成测试
└── docs/                          # 使用、开发、API 和排障文档
```

## 4. 深度研究执行链路

一次研究请求的主要流程如下：

```text
POST /api/v1/research
  -> 创建任务和 SSE 缓冲区
  -> Planner 拆解最多 3 个子问题
  -> 按 depends_on 划分依赖层
  -> 同一层最多并发执行 2 个子问题
  -> 单个子问题并发执行本地检索与联网搜索
  -> Vector + BM25 + RRF，可选 Rerank
  -> Critique 评估相关性与完整性
  -> 未通过时改写查询并重试，重试 Top-K 不超过 20
  -> 提取实体、事实与摘要传给下一跳
  -> 汇总来源并生成报告
```

任务级模式：

- `auto`：Planner 自主决定并列或依赖关系；
- `parallel`：去掉依赖，所有子问题独立执行；
- `multihop`：强制形成依赖链并传递 working memory。

阶段耗时由 `research_agent/observability/timing.py` 收集，任务完成后通过结果中的 `timings` 返回，可用于定位 LLM、Embedding、Web Search 等瓶颈。

## 5. 常见开发工作流

### 新增后端 API

1. 在 `backend/routers/` 新建或扩展路由；
2. 使用 Pydantic 模型定义请求和响应；
3. 在 `backend/main.py` 通过 `/api/v1` 前缀注册；
4. 根据操作加入 `current_user` 或 `require_permission(...)`；
5. 在 `tests/` 增加成功、参数错误、未登录和越权测试；
6. 同步更新 [API 文档](api.md)。

API 统一推荐使用下面的外层结构：

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

### 新增检索策略

检索实现集中在 `research_agent/retrieval/`。新增策略时：

1. 保持统一的检索结果字段，包括 `chunk_id`、`content`、`metadata` 和各阶段分数；
2. 在 `HybridRetriever` 中接入策略和排序逻辑；
3. 必须透传 `allowed_upload_ids`，禁止绕过权限过滤；
4. 避免在每次请求中重建向量库或 BM25，复用 `retrieval_service`；
5. 增加中文实体精确匹配、多结果融合和空知识库测试；
6. 运行固定评测集，比较 Hit@K、MRR、来源召回率和延迟。

### 新增 SSE 事件

使用 `emit(task_id, event_name, data)` 发出事件。当前主要事件包括：

```text
research_plan_start / research_plan_chunk
research_layer_start / reasoning_query / reasoning_context
retrieval_start / retrieval_result / retrieval_combined
web_search_start / web_search_result
critique_start / critique_result / retry_triggered
synthesis_start / synthesis_chunk
done / error / cancelled / heartbeat / timeout
```

新增事件时要同时更新前端 `useResearch` 的处理逻辑。事件数据应可 JSON 序列化，终态事件只能使用 `done`、`error` 或 `cancelled`，否则订阅不会正常结束。

### 新增前端页面

1. 在 `frontend-vue/src/pages/` 创建页面；
2. 在 `frontend-vue/src/router/index.ts` 注册路由与权限元信息；
3. 在 `SideNav.vue` 增加入口；
4. API 调用统一放入 `src/api/`，复用带 Token 的 HTTP 封装；
5. 管理员页面必须同时有前端路由限制和后端权限校验。

## 6. 测试、构建与提交前检查

后端测试：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests -q
```

前端类型检查与生产构建：

```bash
cd frontend-vue
npm run build
```

检索评测：

```bash
.venv/bin/python scripts/evaluate_retrieval.py --top-k 10
```

提交前至少执行：

```bash
git diff --check
.venv/bin/python -m pytest tests -q
cd frontend-vue && npm run build
```

不要提交以下文件：

- `config/.env` 和任何真实 API Key；
- `data/auth.db`；
- `data/uploads/` 与本地向量库；
- 日志、构建产物和用户隐私文档。

## 7. 当前架构限制

- 任务、SSE 缓冲区与 BM25 缓存在进程内，多进程或多副本需要 Redis/队列等共享基础设施；
- 前端研究报告只保存在当前页面内存中，刷新页面或切换账号会清空；后端已完成任务在进程内仍可能短暂存在，但不会被前端自动恢复；
- SQLite 适合单机开发，生产多实例建议迁移 PostgreSQL；
- 文档元数据目前还保存在 `data/uploads/files.json`，并发写入和事务能力有限；
- SSE 鉴权允许查询参数 Token 以兼容原生 `EventSource`，生产环境应使用 HTTPS，并考虑 Cookie 或支持请求头的流式客户端；
- 配置页面会写入 `config/.env`，生产环境应改用 Secret Manager 或部署平台环境变量。

遇到启动、依赖、代理、Embedding 或限流问题，请查看 [故障排查](troubleshooting.md)。
