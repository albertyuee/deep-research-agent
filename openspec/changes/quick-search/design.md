# Quick Search — Design

## Backend

`POST /api/v1/quick-search` → HybridRetriever.search() → LLM summarization → `{ summary, sources, elapsed_ms }`

一次 HTTP 请求-响应，不走 SSE/LangGraph。

## Frontend

Chat UI at `/quick-search`:
- ChatPanel — 消息列表 + 输入区
- ChatMessage — 用户/AI 消息气泡
- ChatInput — 输入框 + 发送按钮
- SuggestionChips — 建议问题标签
