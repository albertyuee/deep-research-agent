## Context

当前 `frontend/components/agent_progress.py` 的 `render_progress_panel()` 函数负责渲染 Agent 进度面板，包含：
- 阶段时间线（分解 → 检索 → 评估 → 合成）
- 当前状态文本
- 研究计划（子问题 + 推荐策略）
- 质量评分摘要
- 进度条

所有 SSE 事件通过 `AgentProgressDisplay.handle_event()` 处理，解析后存储到 `st.session_state`，然后 `render_progress_panel()` 从中读取并渲染。数据流：

```
SSE Events → handle_event() → st.session_state → render_progress_panel() → UI
```

现有事件类型（10 种）：`research_plan_start`, `research_plan_chunk`, `retrieval_start`, `retrieval_result`, `critique_start`, `critique_result`, `retry_triggered`, `synthesis_start`, `synthesis_chunk`, `done`, `error`

**约束**：不修改后端、不修改 SSE 事件格式、不增加 API 调用。所有改进仅在前端实现。

## Goals / Non-Goals

**Goals:**
- 增加实时事件日志区，显示所有 SSE 事件的时间线和关键数据
- 增强各阶段详细信息：检索结果预览、评分推理文字、重试历史
- 增加每个阶段的耗时统计
- 所有新增内容默认折叠，不影响主流程视觉效果

**Non-Goals:**
- 不修改后端 SSE 事件格式或添加新事件类型
- 不添加新的 Python 依赖
- 不改变前端整体布局（仍为左右两栏：进度 + 报告）
- 不添加持久化日志存储

## Decisions

### 1. 数据存储：复用 `st.session_state.agent_steps`

现有代码中 `handle_event()` 已经将每个事件追加到 `st.session_state["agent_steps"]`（第 50 行）。利用这个已有的完整事件历史来渲染日志区，无需新增状态变量。

**替代方案**：新建独立的 `event_log` 状态变量 → 不采纳，因为数据完全重复。

### 2. 日志展示：可折叠展开的 3 层结构

```
┌─ 📋 研究计划 (已有) ─────────────────────┐
├─ 🔍 检索质量详情 (已有) ──────────────────┤
├─ 📜 事件日志 [展开/折叠] ← 新增 ──────────┤
│   time │ event_type         │ data summary │
│   0.0s  │ research_plan_start │ query: "...    │
│   2.3s  │ research_plan_chunk │ #1 什么是RAG... │
│   ...                                        │
│   [点击某行展开查看完整 payload]                 │
├─ ⏱ 阶段耗时 [展开/折叠] ← 新增 ──────────────┤
│   拆解问题: 2.3s                              │
│   检索: 1.5s                                  │
│   评估: 0.8s                                  │
│   合成报告: 5.2s                              │
│   ─────────────                              │
│   总计: 9.8s                                 │
├─ 🔄 重试历史 [展开/折叠] ← 新增 ──────────────┤
│   (仅在发生重试时显示)                         │
└────────────────────────────────────────────┘
```

采用 `st.expander` 实现折叠，默认全部折叠。事件日志使用 `st.dataframe` 或自定义表格展示。

### 3. 耗时计算：基于 SSE 事件到达时间

使用事件到达时间戳（首次见到某阶段事件 → 该阶段完成事件的时间差）计算各阶段耗时。在 `handle_event()` 中记录每个阶段的开始和结束时间戳。

### 4. 代码组织：在 `agent_progress.py` 内扩展

在 `render_progress_panel()` 末尾追加新面板渲染函数，保持向后兼容。新增辅助函数：
- `_render_event_log()` — 事件日志面板
- `_render_timing_stats()` — 耗时统计面板
- `_render_retry_history()` — 重试历史面板

这些函数通过 `from agent_progress import ...` 一样可被调用，保持模块结构清晰。

## Risks / Trade-offs

- `st.session_state.agent_steps` 在长时间运行中可能积累大量事件 → 影响不大，单次研究任务约 20-40 个事件
- 事件日志包含完整 payload，可能暴露内部细节 → 正合用户需求（"详细日志输出"）
- Streamlit 的 `st.expander` 在折叠状态下不渲染子内容 → 性能无影响
