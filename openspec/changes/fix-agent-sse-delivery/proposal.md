## Why

Agent 在 uvicorn 中运行时，SSE 流收到 0 个事件。任务在后台正常完成，但前端看不到任何进度更新。根本原因有三个：LangGraph 条件路由函数修改 state 导致死锁、`task_id` 被 LangGraph 的 TypedDict 过滤掉导致事件静默丢弃、asyncio.Queue 在 StreamingResponse 中事件传递不稳定。

## What Changes

- `state.py`: `ResearchState` TypedDict 新增 `task_id: str` 字段
- `graph.py`: `should_retry` 条件路由函数改为纯读函数，状态修改逻辑移到 `critique_node` 内部
- `streaming.py`: EventBus 从 `asyncio.Queue` 改为 `list` 缓冲区 + `asyncio.Event` 信号机制，增加 2s 心跳事件
- `backend/routers/research.py`: 增加 debug 日志

## Capabilities

### Modified Capabilities
<!-- These are bug fixes, no spec-level requirement changes -->

## Impact

- 核心修复，影响整个 SSE 事件传递链路
- 向后兼容，不改变 API 接口
