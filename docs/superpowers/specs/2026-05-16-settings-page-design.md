# 系统设置页面 — 设计文档

## 概述

实现 `/settings` 页面的系统配置功能，支持修改 LLM、嵌入模型、检索参数并热重载生效，展示系统状态信息。

## 后端 API

### GET /api/v1/settings

返回当前所有配置（掩码 API Key）。

```json
{
  "llm": { "provider": "siliconflow", "model": "Qwen/Qwen3-8B", "api_key": "sk-***", "base_url": "", "temperature": 0.3, "max_tokens": 4096 },
  "embedding": { "mode": "api", "model": "BAAI/bge-large-zh-v1.5", "device": "cpu", "api_base_url": "https://api.siliconflow.cn/v1", "api_key": "sk-***" },
  "retrieval": { "top_k": 5, "max_retries": 3, "critique_threshold": 0.6 }
}
```

### PATCH /api/v1/settings

部分更新配置，写入 `.env` 文件。返回更新后的完整配置。

```json
// Request
{ "llm": { "temperature": 0.5 }, "retrieval": { "top_k": 8 } }

// Response
{ "success": true, "data": { "updated": ["llm.temperature", "retrieval.top_k"], "need_restart": false } }
```

### GET /api/v1/settings/system-info

```json
{ "chroma_chunks": 120, "chroma_collections": 1, "version": "0.1.0" }
```

## 前端

### 页面布局

`/settings` — 分组表单，每组分 card 展示

- **LLM 配置**: provider 下拉、api_key 密码框、model 下拉、temperature 滑块、max_tokens 数字输入
- **嵌入模型**: mode 单选、model 下拉、api_key 密码框
- **检索配置**: top_k 数字输入、critique_threshold 滑块、max_retries 数字输入
- **系统信息**: ChromaDB 统计、版本号（只读）
- 底部「保存配置」按钮 → PATCH → 成功提示

### 组件

| 组件 | 说明 |
|------|------|
| `SettingsPage.vue` | 页面主体 |
| `SettingsSection.vue` | 分组卡片包装 |
| `SystemInfo.vue` | 系统信息卡片 |

## 热重载机制

修改 LLM/Embedding/Retrieval 参数 → 更新 settings 对象 → 下次 LLM/嵌入调用即生效。ChromaDB 路径等基础设施参数标记 `need_restart: true`。

## 不在范围内

- Milvus 配置（使用 ChromaDB）
- 多用户/角色权限
- 配置导入导出
