# 故障排查

先确认命令在项目根目录执行，并优先查看 `./start.sh` 输出和 `logs/` 中的后端日志。不要把日志中的 API Key、Token、数据库连接串粘贴到公开 Issue。

## 1. `./start.sh` 启动失败

检查端口：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

确认是本项目旧进程后再停止，使用上一条命令显示的 PID：

```bash
kill <PID>
```

如果普通停止无效，再使用：

```bash
kill -9 <PID>
```

重新运行 `./start.sh`。脚本固定使用 5173 和 `--strictPort`，不会自动切到 5174；端口被占用时会明确失败。

## 2. 登录页空白、未登录仍能访问或 `/auth/me` 返回 404

这通常表示浏览器连接的是旧前端/旧后端，或鉴权没有真正开启。

1. 确认 `config/.env` 中为 `AUTH_ENABLED=true`；
2. 停止 8000、5173 端口上的旧进程；
3. 重新运行 `./start.sh`；
4. 打开 `http://localhost:8000/docs`，确认存在 `/api/v1/auth/me`；
5. 未携带 Token 请求应返回 401：

```bash
curl -i http://localhost:8000/api/v1/auth/me
```

`localhost` 与 `127.0.0.1` 是两个不同的浏览器来源，本地存储的登录 Token 不共享。开发期间建议始终使用同一个主机名。

## 3. Python 使用了全局环境

如果 Traceback 指向 `/Library/Frameworks/Python.framework/.../site-packages`，说明没有使用项目 `.venv`。

```bash
./start.sh

# 或手动验证
.venv/bin/python -c "import sys; print(sys.executable)"
```

输出应位于项目的 `.venv/bin/python`。

## 4. Chroma/Pydantic 报 `_signature` 不存在

典型错误：

```text
ModuleNotFoundError: No module named 'pydantic._internal._signature'
```

原因通常是全局环境中 `pydantic`、`pydantic-settings` 与 `chromadb` 版本混装。重建项目虚拟环境：

```bash
mv .venv .venv.bak
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

验证成功后再删除 `.venv.bak`。不要用全局 `pip install` 修补项目依赖。

## 5. SOCKS 代理缺少 `socksio`

典型错误：

```text
Using SOCKS proxy, but the 'socksio' package is not installed
```

项目依赖已声明 `httpx[socks]`。在项目虚拟环境修复：

```bash
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -c "import socksio; print('socksio ok')"
```

代理示例：

```bash
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890
export no_proxy=127.0.0.1,localhost
./start.sh
```

## 6. Embedding API 返回 400

`400 Bad Request` 一般是模型名、接口地址、请求格式、维度或文本长度不符合上游要求。

检查：

- `EMBEDDING_MODE=api`；
- `EMBEDDING_API_BASE_URL` 通常以 `/v1` 结尾，不要重复拼接 `/embeddings`；
- `EMBEDDING_MODEL` 是供应商实际支持的 Embedding 模型；
- API Key 有该模型权限；
- 向量库维度与当前模型输出维度一致；
- 输入没有超过 `EMBEDDING_QUERY_MAX_CHARS` 和供应商限制。

先在“系统设置”测试 Embedding 连接。更换模型或维度后，旧向量库通常需要重新建库并重新索引文档。

## 7. API 返回 429

`429 Too Many Requests` 表示上游限流、并发过高、额度不足或服务繁忙。SiliconFlow 的 `50609 / System is too busy now` 通常是服务端繁忙。

处理建议：

- 等待一段时间后重试；
- 将 `RETRIEVAL_MAX_CONCURRENCY` 保持为 2 或更低；
- 减少联网搜索、Rerank 或同时运行的研究任务；
- 检查账户额度和模型并发限制；
- 为上游调用增加指数退避和随机抖动，避免立即连续重试。

不要把 429 当成检索无结果，也不要无限重试。

## 8. Milvus/Zilliz 连接失败

检查 `RETRIEVAL_VECTOR_BACKEND=milvus`，并二选一配置：

- Zilliz Cloud：`MILVUS_URI` + `MILVUS_TOKEN`；
- 自建 Milvus：`MILVUS_HOST` + `MILVUS_PORT`。

本机启用了代理时，将 Milvus/Zilliz 主机加入 `no_proxy`。HTTP/SOCKS 代理可能破坏 gRPC TLS 握手。可先通过“系统设置 → 测试连接”确认，再上传或检索文档。

## 9. 获取文档列表返回 500

按顺序检查：

1. 后端日志中的真实异常；
2. 当前向量后端能否连接；
3. `data/uploads/files.json` 是否为合法 JSON；
4. 文档元数据是否包含可解析的 `upload_id`；
5. 当前进程对 `data/` 是否有读写权限；
6. Chroma/Milvus 中的 Embedding 维度是否与当前配置一致。

不要直接删除用户数据。先备份 `data/uploads/`、`files.json` 和向量库，再进行修复。

## 10. 上传显示失败或没有反馈

上传接口只有在以下步骤全部完成后才返回成功：保存文件、解析、切块、向量索引、BM25 重建、写入元数据。大文件或远程 Embedding 会让上传耗时较长。

检查：

- 文件属于 PDF、DOCX、Markdown、TXT；
- 文件不超过 20 MB 且不是空文档；
- Embedding 和向量库连接正常；
- 当前角色拥有 `document:upload`；
- `department` 模式下用户已加入部门；
- `departments` 模式仅由管理员使用，并至少选择一个部门。

收到成功提示后刷新资料列表，文件状态应为 `ready` 且分块数大于 0。

## 11. 快速检索找不到已上传资料

先在资料管理页确认文档处于 `ready`，再检查：

- 当前账号是否在该文档 ACL 内；
- 文档 `id` 是否与向量块的 `upload_id` 一致；
- 上传使用的向量后端是否与当前 `RETRIEVAL_VECTOR_BACKEND` 相同；
- 中文姓名等精确词是否被 BM25 正确索引；
- `top_k` 是否过小；
- 日志中的 `returned`、`sources`、BM25/向量/Rerank 分数。

可以先关闭 Rerank 做对照测试，判断问题发生在召回阶段还是精排阶段。

## 12. 深度研究报告消失、耗时为 0 或 SSE 中断

确认浏览器没有连接旧前端，并查看 Network 中：

- `POST /api/v1/research` 是否成功；
- SSE 是否收到 `done`；
- `GET /api/v1/research/{task_id}` 是否仍返回已完成结果；
- Token 是否过期；
- 是否混用了 `localhost` 和 `127.0.0.1`。

当前任务和 SSE 缓冲区保存在内存，重启后端会丢失未持久化任务；终态 SSE 事件只保留短时间供迟到订阅者读取。生产环境需要把任务状态、事件和报告迁移到持久化存储。

## 13. 测试或构建失败

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests -q

cd frontend-vue
npm install
npm run build
```

若只有本地失败，记录 Python、Node 和 npm 版本，并确认没有用全局依赖覆盖 `.venv` 或 `node_modules`。

## 14. 仍无法定位

收集以下信息再排查：

```bash
.venv/bin/python --version
node --version
npm --version
curl -i http://localhost:8000/health
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

同时保留完整错误堆栈、触发步骤、接口状态码和最近一次配置变更；分享前必须删除 API Key、Bearer Token、数据库密码及用户文档内容。
