## 1. Fix stream_chat IndexError

- [x] 1.1 Add `if not chunk.choices: continue` guard before accessing `chunk.choices[0]`
- [x] 1.2 Also check `if delta.content:` before yielding (skip None/empty content)

## 2. Replace openai library with pure httpx

- [x] 2.1 Rewrite `OpenAIClient` to use `httpx.AsyncClient` directly instead of `AsyncOpenAI`
- [x] 2.2 Implement `_post()`, `_build_body()`, `_retry()` helper methods
- [x] 2.3 Rewrite `stream_chat` to use `client.stream()` with manual SSE line parsing
- [x] 2.4 Rewrite `chat_structured` to copy messages before appending schema prompt

## 3. Add timeout and retry

- [x] 3.1 Set default timeout to 120s with 30s connect timeout
- [x] 3.2 Implement `_retry()` with exponential backoff (1 retry, 2s wait)
- [x] 3.3 Apply retry to all three methods (chat, stream_chat, chat_structured)

## 4. Switch to stable model

- [x] 4.1 Change `LLM_MODEL` in config/.env from `deepseek-ai/DeepSeek-V4-Flash` to `deepseek-ai/DeepSeek-V3`
