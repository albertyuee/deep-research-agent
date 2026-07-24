# 权限管理

当前权限系统是第一期单机实现：FastAPI 负责身份认证和授权，本地 SQLite 保存用户、部门、会话及预留的 ACL 表；文档访问范围目前写入 `data/uploads/files.json`，并同步到向量块元数据。它适合本地开发、演示和小规模单机部署。

## 1. 开启权限

在 `config/.env` 中配置：

```env
AUTH_ENABLED=true
AUTH_DB_PATH=data/auth.db
AUTH_ADMIN_EMAIL=admin@example.com
AUTH_ADMIN_PASSWORD=请设置至少8位的强密码
AUTH_ADMIN_NAME=系统管理员
```

然后重启：

```bash
./start.sh
```

首次启动会自动创建数据库表和初始管理员。访问 `http://localhost:5173/login` 登录，管理员后台位于 `http://localhost:5173/admin`。

> `AUTH_ENABLED=false` 时系统使用一个合成管理员以兼容原来的单用户演示模式，所有文档均可访问。不要在面向公网的环境关闭鉴权。

## 2. 角色与权限

| 权限 | admin | researcher | guest |
|---|:---:|:---:|:---:|
| 查看可访问文档 | ✓ | ✓ | ✓ |
| 发起研究/快速检索 | ✓ | ✓ | ✓ |
| 取消自己的研究任务 | ✓ | ✓ | — |
| 上传文档 | ✓ | ✓ | — |
| 删除自己的文档 | ✓ | ✓ | — |
| 设置文档共享范围 | ✓ | — | — |
| 查看系统设置 | ✓ | ✓ | — |
| 修改系统设置 | ✓ | — | — |
| 用户和部门管理 | ✓ | — | — |

管理员可以查看所有文档和研究任务。普通用户只能访问自己的研究任务以及 ACL 允许的文档。

## 3. 文档访问范围

| `visibility` | 含义 | 需要的附加字段 |
|---|---|---|
| `private` | 仅上传者和管理员可见 | 无 |
| `department` | 上传者所属的单一部门可见 | 上传者必须已加入部门 |
| `departments` | 指定多个部门可见 | `allowed_departments`；仅管理员可设置 |
| `workspace` | 当前系统内全部已登录用户可见 | 无 |
| `roles` | 指定角色可见 | `allowed_roles` |
| `users` | 指定用户可见 | `allowed_users` |
| `public` | 公开范围；当前仍需通过应用接口访问 | 无 |

拥有者始终可以访问自己的文档；管理员始终可以访问所有文档。

“公开”表示不按用户、角色或部门过滤该文档，并不代表项目已提供无需登录的公开下载地址。当 `AUTH_ENABLED=true` 时，受保护 API 仍要求登录。

## 4. 推荐配置流程

```text
管理员登录
  -> 创建部门
  -> 创建用户
  -> 分配角色与部门
  -> 上传文档并选择初始访问范围
  -> 在管理后台搜索文档并复核 ACL
  -> 用不同角色账号验证资料列表、快速检索和深度研究结果
```

管理员上传时可以选择全部人员可见、单一部门、多个指定部门或更细粒度 ACL。资料管理页会在索引成功后显示文件名、分块数和成功状态；只有返回成功并出现在文件列表中，才表示上传和索引都已完成。

## 5. 权限如何作用于检索

权限校验不只发生在前端：

1. 后端读取当前用户可访问的文档 ID；
2. Chroma 或 Milvus 仅召回这些 `upload_id`；
3. BM25 使用同一允许列表过滤；
4. 快速检索和深度研究共用该过滤规则；
5. 文档列表、删除、ACL 修改、研究任务状态和 SSE 订阅再次独立校验。

因此隐藏菜单或修改前端请求不能绕过文档权限。开发新的检索器时必须继续透传 `allowed_upload_ids`。

## 6. API 鉴权

登录成功后在普通请求中携带：

```http
Authorization: Bearer <token>
```

原生浏览器 `EventSource` 不能设置自定义请求头，因此研究流当前支持：

```text
GET /api/v1/research/{task_id}/stream?access_token=<token>
```

会话默认有效期为 7 天，数据库中只保存 Token 的 SHA-256 摘要。密码使用带随机盐的 PBKDF2-SHA256 哈希，不保存明文。

## 7. 历史文档与迁移注意事项

启用权限前已导入、但缺少 `owner_id` 和 `visibility` 的历史文档，普通用户可能无法访问，管理员仍可查看。上线权限前应：

1. 备份 `data/uploads/files.json` 和向量库；
2. 为每份历史文档补充拥有者和访问范围；
3. 确保文件元数据与向量块的 `upload_id` 一致；
4. 使用管理员、研究员、访客三个账号做回归测试。

不要直接手工编辑生产中的 SQLite 或 `files.json`；优先通过管理后台/API 修改，避免 ACL 与向量元数据不一致。

## 8. SQLite 与 Supabase/PostgreSQL

SQLite 可以完成当前角色、部门和文档权限需求，但适用于单进程或低并发场景。出现以下需求时建议迁移 Supabase PostgreSQL：

- 多台服务器或多个后端副本；
- 需要事务化管理文档元数据与 ACL；
- 需要审计日志、组织级隔离或复杂部门层级；
- 需要 Supabase Auth、JWT、密码找回、邮箱验证或第三方登录。

建议迁移顺序：

1. 将 `users`、`departments`、`document_permissions` 和文档元数据迁入 PostgreSQL；
2. 用 Supabase Auth/JWT 替换本地 session Token；
3. 在 PostgreSQL 启用 Row Level Security；
4. 后端继续做业务授权，RLS 作为第二道防线；
5. 最后迁移任务归属和审计日志。

迁移前不要把 Supabase 数据库密码、service role key 或真实连接串写入 README、源码或 `.env.example`。

## 9. 生产安全清单

- 使用 HTTPS，避免 Token 被明文传输；
- 设置强管理员密码并定期轮换；
- 严格限制 CORS 来源；
- 不提交 `config/.env`、`data/auth.db` 和上传文件；
- 对登录和高成本研究接口增加速率限制；
- 增加用户操作、文档权限变更和失败登录审计；
- 定期备份权限数据库、文档元数据和向量库；
- 多实例部署前迁移 SQLite、内存任务状态和 SSE 事件总线。
