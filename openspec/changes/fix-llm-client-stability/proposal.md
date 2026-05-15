## Why

`openai` 库的 `AsyncOpenAI` 在 uvicorn 事件循环中存在连接池冲突，`stream_chat` 遇到空 `choices` 数组时崩溃（IndexError），`deepseek-ai/DeepSeek-V4-Flash` 非流式接口间歇超时。三个问题叠加导致 Agent 的 LLM 调用频繁失败。

## What Changes

- `openai_client.py`:
  - `stream_chat`: 添加 `if not chunk.choices: continue` 守卫
  - 完全移除 `openai` 库依赖，改用纯 `httpx.AsyncClient` 直接调用 API
  - 添加超时（120s）和指数退避重试机制
  - `chat_structured`: 复制 messages 后再追加 schema prompt，避免修改调用方数据
- `config/.env`: `LLM_MODEL` 从 `deepseek-ai/DeepSeek-V4-Flash` 改为 `deepseek-ai/DeepSeek-V3`

## Capabilities

### Modified Capabilities
<!-- Bug fixes, no spec changes -->

## Impact

- 移除 `openai` 依赖的运行时使用（`import openai` 不再出现在 openai_client.py）
- API 调用从异步库改为 httpx 直连，超时和错误处理更可控
