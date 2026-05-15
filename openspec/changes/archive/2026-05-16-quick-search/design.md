# Quick Search — Design

## Backend

`POST /api/v1/quick-search` → HybridRetriever.search() → LLM summary → `{ summary, sources, elapsed_ms }`

## Frontend

Chat UI at `/quick-search`:
- ChatPanel → 消息列表 + 输入
- ChatMessage → 用户/AI 气泡 + Markdown + 来源
- ChatInput → 输入框 + 发送
- SuggestionChips → 建议问题
