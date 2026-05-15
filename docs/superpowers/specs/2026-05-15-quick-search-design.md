# 快速检索功能 — 设计文档

## 概述

在现有深度研究基础上，新增快速检索功能。绕过 LangGraph 的拆解-评估-合成流水线，直接进行混合检索 + LLM 摘要，实现秒级响应的对话式问答体验。

## 动机

- 深度研究慢（2-5 分钟），需要多次 LLM 调用（拆解、评估、合成、重试）
- 用户很多场景只需要快速查找 + 简短总结，不需要完整报告
- 现有检索基础设施（向量库 + BM25 + RRF）本身很快（<0.5s），瓶颈在 LLM 调用链

## 目标

- 新增后端 `/api/v1/quick-search` 端点，一次请求-响应返回摘要
- 前端 `/quick-search` 页面，对话式 UI
- 一次检索 + 一次 LLM 摘要调用，目标 <5 秒
- 会话内保留对话历史（不持久化）

## 技术决策

| 维度 | 决策 | 原因 |
|------|------|------|
| 协议 | 同步 HTTP（非 SSE）| 快速检索流程短，不需要流式 |
| 检索 | 复用 HybridRetriever | 零改动，直接调用 |
| 摘要 | 一次 LLM 调用 | 用检索结果作为 context |
| 历史 | 前端 Pinia store | 简单，不需要后端存储 |
| 路由 | 独立端点 `/api/v1/quick-search` | 与深度研究隔离，易扩展 |

## 后端 API

### POST /api/v1/quick-search

**Request:**
```json
{
  "query": "Transformer为什么比LSTM好？",
  "top_k": 5
}
```

**Internal Flow:**
```
1. HybridRetriever.search(query, top_k)        # ~0.3s
2. LLM Chat(system_prompt + context + query)   # ~3s
   system_prompt: "你是一个研究助手。基于以下检索结果，用中文简洁地回答用户问题。如果检索结果不足以回答问题，如实告知用户。"
   context: top_k 条结果的 content 拼接
3. Return { summary, sources, elapsed }
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "Transformer为什么比LSTM好？",
    "summary": "Transformer相比LSTM的主要优势在于：1) 并行计算能力——Transformer的自注意力机制允许同时处理整个序列...",
    "sources": [
      {
        "chunk_id": "transformer_vs_lstm_chunk_0",
        "content": "...",
        "score": 0.85,
        "metadata": { "doc_title": "Transformer Architecture Review", "strategy": "hybrid" }
      }
    ],
    "elapsed_ms": 3200
  },
  "error": null
}
```

### Error Handling

- 检索器未初始化：500，提示检查向量库
- LLM 调用失败：500，返回错误信息
- 空检索结果：200，summary 告知用户无相关信息
- query 为空：400

## 前端

### 页面布局

```
/quick-search
┌──────────────────────────────────────────┐
│ QuickSearchPage.vue                       │
│ ┌────────────────────────────────────────┐│
│ │ ChatPanel.vue                          ││
│ │  ┌──────────────────────────────────┐  ││
│ │  │ 消息列表（v-for messages）        │  ││
│ │  │  🙋 用户消息（右侧蓝色气泡）       │  ││
│ │  │  🤖 AI消息（左侧灰色气泡）         │  ││
│ │  │    ├── Markdown 摘要文本           │  ││
│ │  │    └── 📎 来源（可折叠 n-card）    │  ││
│ │  └──────────────────────────────────┘  ││
│ │  ┌──────────────────────────────────┐  ││
│ │  │ 💡 建议问题 chips                  │  ││
│ │  │ [输入框]                    [发送] │  ││
│ │  └──────────────────────────────────┘  ││
│ └────────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

### 组件树

```
QuickSearchPage.vue
└── ChatPanel.vue                   # 页面主体：消息列表 + 底部输入
    ├── ChatMessage.vue (× N)      # 单条消息气泡
    │   ├── [AI]: n-text (Markdown 摘要) + SourceCard (折叠)
    │   └── [User]: n-text (纯文本)
    └── 底部区域:
        ├── SuggestionChips         # 建议问题 n-tag 列表
        └── ChatInput               # n-input + n-button 发送
```

### Pinia Store — chat.ts

```typescript
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string          // AI: 摘要文本 / User: 问题文本
  sources?: Source[]       // 仅 AI 消息有
  timestamp: number
}

// Store
messages: Ref<ChatMessage[]>
isLoading: Ref<boolean>
error: Ref<string | null>

// Actions
sendMessage(query: string)   // POST quick-search, push user + assistant messages
clearHistory()               // 清空消息列表
```

### 数据流

```
用户在 ChatInput 输入 → Enter/点击发送
  → pinia.chat.sendMessage(query)
  → POST /api/v1/quick-search { query, top_k: 5 }
  → isLoading = true
  → 收到响应
  → messages.push(userMessage)
  → messages.push(assistantMessage(summary, sources))
  → isLoading = false
  → nextTick → 滚动到底部
```

### 关键交互细节

- Enter 发送，Shift+Enter 换行
- 发送中显示 loading 动画（三个点跳动）
- AI 消息中的 Markdown 用 `marked` 渲染
- 来源默认折叠，点击展开显示内容和分数
- 空状态：显示欢迎语 + 建议问题 chips
- 错误状态：显示 n-alert 错误提示

## 不在范围内

- 多轮对话上下文（每轮独立）
- 对话历史持久化
- 检索策略选择（默认 hybrid）
- 深度研究现有流程的改动
- 后端 VectorStore/BM25/HybridRetriever 改动

## 文件清单

### 新建

| 文件 | 说明 |
|------|------|
| `backend/routers/quick_search.py` | Quick Search API 路由 |
| `frontend-vue/src/stores/chat.ts` | 对话状态 Pinia Store |
| `frontend-vue/src/api/chat.ts` | quickSearch() HTTP 调用 |
| `frontend-vue/src/components/chat/ChatPanel.vue` | 聊天面板主体 |
| `frontend-vue/src/components/chat/ChatMessage.vue` | 单条消息气泡 |
| `frontend-vue/src/components/chat/ChatInput.vue` | 输入框 + 发送按钮 |
| `frontend-vue/src/components/chat/SuggestionChips.vue` | 建议问题标签 |

### 修改

| 文件 | 改动 |
|------|------|
| `backend/main.py` | 注册 quick_search router |
| `frontend-vue/src/pages/QuickSearchPage.vue` | 替换占位页面 |
| `frontend-vue/src/router/index.ts` | 无需改动（路由已存在） |
