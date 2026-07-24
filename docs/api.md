# API 文档

默认 API 根地址为：

```text
http://localhost:8000/api/v1
```

交互式 OpenAPI 文档：`http://localhost:8000/docs`。本文列出稳定的业务接口和常用示例，字段的最终约束以运行中的 OpenAPI Schema 为准。

## 1. 通用约定

JSON 请求使用：

```http
Content-Type: application/json
```

开启权限后，除登录接口外请携带：

```http
Authorization: Bearer <token>
```

大部分接口使用统一外层：

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

FastAPI 参数校验错误使用标准 `detail` 结构。常见状态码：

| 状态码 | 含义 |
|---|---|
| `400` | 参数或业务条件不合法 |
| `401` | 未登录、Token 无效或已过期 |
| `403` | 已登录但权限不足 |
| `404` | 用户、文档或研究任务不存在 |
| `409` | 邮箱冲突或任务状态冲突 |
| `413` | 上传文件超过 20 MB |
| `422` | Pydantic 请求字段校验失败 |
| `429` | 上游模型/搜索服务限流 |
| `500` | 后端、向量库或上游服务异常 |

## 2. Auth API

### 登录

```http
POST /api/v1/auth/login
```

```json
{
  "email": "admin@example.com",
  "password": "your-password"
}
```

响应的 `data.token` 用于后续 Bearer 鉴权，`data.user.permissions` 是当前角色的权限列表。

### 当前用户

```http
GET /api/v1/auth/me
```

### 用户管理（管理员）

```http
GET    /api/v1/auth/users
POST   /api/v1/auth/users
PATCH  /api/v1/auth/users/{user_id}
DELETE /api/v1/auth/users/{user_id}
```

创建用户：

```json
{
  "email": "researcher@example.com",
  "password": "at-least-8-characters",
  "display_name": "研究员",
  "role": "researcher",
  "department_id": "department-id-or-null"
}
```

更新用户可传部分字段：

```json
{
  "display_name": "新名称",
  "role": "guest",
  "department_id": null,
  "active": true,
  "password": "new-password"
}
```

角色只允许 `admin`、`researcher`、`guest`。不能禁用或删除当前登录的管理员。

### 部门管理

```http
GET  /api/v1/auth/departments
POST /api/v1/auth/departments
```

普通用户可读取部门列表，只有管理员可创建：

```json
{
  "name": "研发部",
  "parent_id": null
}
```

## 3. Research API

### 创建研究任务

```http
POST /api/v1/research
```

```json
{
  "query": "GraphRAG、LangGraph 和 LlamaIndex 在深度研究系统中分别承担什么职责？",
  "enable_web_search": true,
  "research_mode": "multihop",
  "max_hops": 3
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `query` | string | 是 | 研究问题，不能为空 |
| `enable_web_search` | boolean | 否 | 是否同时使用联网搜索，默认 `false` |
| `research_mode` | string | 否 | `auto`、`parallel`、`multihop`，默认 `auto` |
| `max_hops` | integer/null | 否 | `1`～`8`，省略时使用系统配置 |

响应中的 `data.task_id` 用于状态查询和 SSE 订阅。

### 查询状态

```http
GET /api/v1/research/{task_id}
```

完成结果的 `data.result` 包含：

- `report`：最终 Markdown 报告；
- `sub_queries`：拆解后的子问题；
- `sources`：引用来源；
- `low_confidence_steps`：低置信度步骤；
- `hop_count`、`reasoning_paths`、`step_contexts`：多跳信息；
- `research_mode`：实际研究模式；
- `timings`：LLM、Embedding、Web Search 等阶段耗时。

### 订阅 SSE

```http
GET /api/v1/research/{task_id}/stream
```

开启权限且使用原生 `EventSource` 时：

```js
const stream = new EventSource(
  `/api/v1/research/${taskId}/stream?access_token=${encodeURIComponent(token)}`
)

stream.onmessage = (message) => {
  const payload = JSON.parse(message.data)
  console.log(payload.event, payload.data)
}
```

每条消息格式：

```text
data: {"event":"retrieval_result","data":{...}}
```

主要事件见 [开发指南的 SSE 章节](development.md#新增-sse-事件)。`done`、`error`、`cancelled` 为终态，空闲期间会收到 `heartbeat`，连续空闲 600 秒后收到 `timeout`。

### 取消任务

```http
POST /api/v1/research/{task_id}/cancel
```

只有任务所有者或管理员可以取消，且任务必须处于 `running` 状态。

## 4. Quick Search API

```http
POST /api/v1/quick-search
```

```json
{
  "query": "刘悦是谁？",
  "top_k": 5,
  "history": [
    {"role": "user", "content": "介绍一下研发团队"},
    {"role": "assistant", "content": "团队包括……"}
  ]
}
```

约束：

- `query` 长度 1～1000；
- `top_k` 范围 1～20，默认 5；
- `history` 最多 20 条，只接受 `user` 和 `assistant`；
- 检索改写实际只使用最近 8 条，每条最多 1500 字符。

接口执行混合检索并生成不超过约 300 字的中文摘要，响应包含 `summary`、来源和耗时等数据。

## 5. Documents API

### 文档列表

```http
GET /api/v1/documents
```

只返回当前用户可以访问的文档，主要字段包括 `id`、`name`、`size`、`chunks`、`status`、`uploaded_at` 和 ACL 信息。

### 上传并索引

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
```

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./example.pdf" \
  -F "visibility=departments" \
  -F "department_ids=department-a,department-b"
```

表单字段：

| 字段 | 说明 |
|---|---|
| `file` | PDF、DOCX、Markdown 或 TXT，最大 20 MB |
| `visibility` | 访问范围，默认 `private` |
| `department_ids` | 多个部门 ID，用英文逗号分隔 |
| `allowed_roles` | 多个角色，用英文逗号分隔 |
| `allowed_users` | 多个用户 ID，用英文逗号分隔 |

上传成功表示文件保存、切块、向量索引和 BM25 重建均已完成；失败时会尝试回滚本次向量索引和临时文件。

### 修改文档权限（管理员）

```http
PATCH /api/v1/documents/{file_id}/access
```

```json
{
  "visibility": "departments",
  "department_id": null,
  "allowed_departments": ["department-a", "department-b"],
  "allowed_roles": [],
  "allowed_users": []
}
```

`roles`、`users`、`departments` 模式必须提供相应的非空允许列表。完整语义见 [权限管理](permissions.md#3-文档访问范围)。

### 删除文档

```http
DELETE /api/v1/documents/{file_id}
```

管理员可删除任意文档；普通用户只能删除自己上传的文档。接口会删除向量块、重建 BM25、删除文件目录和元数据。

## 6. Settings API

```http
GET   /api/v1/settings
PATCH /api/v1/settings
POST  /api/v1/settings/test-connection
GET   /api/v1/settings/system-info
```

- `GET /settings`：管理员和研究员可读，API Key 以掩码返回；
- `PATCH /settings`：仅管理员，可部分更新 LLM、Embedding、Retrieval、Reasoning、Rerank、Milvus、MCP、LangSmith；
- `POST /settings/test-connection`：仅管理员，`service` 支持 `llm`、`embedding`、`milvus`、`langsmith`；
- `GET /settings/system-info`：返回向量后端、块数量和应用版本。

更新示例：

```json
{
  "retrieval": {
    "top_k": 5,
    "max_top_k": 20,
    "max_concurrency": 2
  },
  "reasoning": {
    "enabled": true,
    "max_sub_queries": 3,
    "max_hops": 3
  }
}
```

设置接口会写入 `config/.env` 并清理部分后端缓存；LangSmith 等进程级配置可能仍需要重启。

## 7. 健康检查

健康检查不在 `/api/v1` 前缀下：

```http
GET /health
```

可用于启动脚本、容器探针或反向代理健康检查。
