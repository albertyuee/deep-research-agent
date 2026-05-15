## Why

前端在长时间 Agent 运行中出现 SSE 连接中断、Streamlit 组件 key 冲突导致渲染静默失败、`research_plan_start` 被手动触发两次导致 event_log 被清空。

## What Changes

- `app.py`:
  - 移除手动触发的 `research_plan_start`（SSE 流会自行发送）
  - SSE 流超时从 300s 改为 600s/30s
  - 新增 `httpx.ReadTimeout`、`httpx.ConnectTimeout` 单独错误处理
- `agent_progress.py`:
  - 所有 `st.expander` 添加唯一动态 key（`payload_{i}_{len}` 等）
  - `st.json()` 添加 try/except 降级处理
  - 心跳事件跳过 event_log 记录

## Capabilities

### Modified Capabilities
<!-- Bug fixes, no spec changes -->

## Impact

- 仅修改前端组件，不影响后端
- Streamlit 渲染不再因 key 冲突静默失败
