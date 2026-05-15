## Context

当前前端使用 `asyncio.run(run_research())` 直接阻塞 Streamlit 主线程来等待 SSE 事件流。这导致研究运行期间 UI 完全无法交互。后端 `_run_agent()` 通过 `asyncio.create_task()` 启动 agent 但不保存 task 引用，因此无法从外部取消。

页面布局方面，`st.columns([1, 2])` 在 idle 状态下仍渲染左侧空的进度面板；welcome 区域只在 `text-align: center` 下未在容器中垂直居中；调试信息使用 `st.sidebar` 始终可见且占用侧边栏空间。

## Goals / Non-Goals

**Goals:**
- 用户可在研究运行中随时点击停止按钮立即终止
- 前端在研究运行期间保持 UI 可交互
- 停止后保留已生成的部分报告和进度数据
- idle 状态下 welcome 区域全宽居中显示
- 调试面板改为可收起/展开的滑出式 drawer
- 运行中在顶部显示状态栏（进度条 + 阶段 + 耗时 + 停止按钮）

**Non-Goals:**
- 不改变 agent graph 内部逻辑（取消仅依赖 asyncio.Task.cancel()）
- 不改变现有事件类型或 SSE 格式
- 不改变报告渲染组件的外部接口
- 不支持暂停/恢复（只支持立即停止）

## Decisions

### 1. 前端异步架构：`threading.Thread` + `queue.Queue`

**选择**：用一个独立的 Python thread 运行 `asyncio` event loop，通过 `queue.Queue` 将事件传递给 Streamlit 主线程。

```
┌─ 主线程 (Streamlit) ─┐       ┌─ worker 线程 ──────────┐
│                       │       │                         │
│  检查 queue.get()     │◀──────│  asyncio event loop     │
│  更新 session_state   │ queue │  SSE 流读取 + 事件处理  │
│  st.rerun() 重渲染   │       │                         │
│                       │       │  收到 cancel 信号        │
│  [🛑 ] 设置 cancel    │──────▶│  → httpx 断开 + 清理    │
│        flag           │       │                         │
└───────────────────────┘       └─────────────────────────┘
```

**备选方案**：
- `@st.fragment`：需要 Streamlit 1.33+，且只能局部重渲染，不能解决阻塞问题 — 不采用
- 子进程：复杂度高，进程间通信开销大 — 不采用

**轮询机制**：worker 线程将每个 SSE 事件放入 `queue.Queue`；主线程在每个 rerun 周期中消费队列中的所有事件并更新 `session_state`，然后调用 `st.rerun()` 触发下一轮。空闲时使用 `time.sleep(0.2)` 防止过度循环。

### 2. 后端取消机制

**选择**：`POST /api/v1/research/{task_id}/cancel` + `asyncio.Task.cancel()`

`_run_agent()` 启动时将 `asyncio.Task` 引用存入 `ResearchTaskManager._running_tasks[task_id]`。cancel 端点获取该引用并调用 `task.cancel()`，触发 `CancelledError`。

关键处理：
```python
# _run_agent 中的改动
try:
    result = await agent_graph.ainvoke(initial_state)
except asyncio.CancelledError:
    event_bus.emit(task_id, "cancelled", {
        "message": "研究已被用户取消",
        "partial_report_length": len(accumulated_report_text),
    })
    task_manager.update_status(task_id, TaskStatus.CANCELLED)
finally:
    event_bus.cleanup(task_id)
```

**风险**：LangGraph 的 `ainvoke` 可能内部捕获 `CancelledError`。缓解方案：如果测试发现 cancel 信号无法传播进 graph，则在 graph 节点中通过 event bus 的 cancel flag 主动检查。

### 3. 布局状态机

**选择**：基于 `session_state["page_state"]` 动态渲染不同布局

四种状态：`idle` | `running` | `completed` | `cancelled`

| 页面区域 | idle | running | completed | cancelled |
|----------|------|---------|-----------|-----------|
| 输入区域 | 全宽 | 紧凑的 status bar 内侧 | 全宽（可重新搜索） | 全宽（可重新搜索） |
| 左列（进度） | 隐藏 | 显示，1/3 宽 | 显示，1/3 宽 | 显示，1/3 宽 |
| 右列（报告） | 全宽，welcome 居中 | 显示，2/3 宽 | 显示，2/3 宽 | 显示，2/3 宽 |
| 状态栏 | 不显示 | 显示（阶段+进度+耗时+停止） | 不显示 | 显示已完成/取消提示 |
| 调试抽屉 | 隐藏可触发 | 隐藏可触发 | 隐藏可触发 | 隐藏可触发 |

### 4. 调试抽屉实现方式

**选择**：CSS-based slide-out panel，用 `st.session_state["show_debug"]` 控制

```html
<!-- 固定齿轮按钮 -->
<div class="debug-toggle" onclick="...">⚙️</div>

<!-- 滑出面板 -->
<div class="debug-drawer {open/closed}">
  <div class="debug-drawer-header">
    <span>📋 调试面板</span>
    <button class="debug-drawer-close">✕</button>
  </div>
  <div class="debug-drawer-body">
    <!-- Streamlit 渲染的调试内容 -->
  </div>
</div>

<!-- 遮罩层 -->
<div class="debug-overlay {active/inactive}"></div>
```

由于 Streamlit 原生不支持 JS 交互，需要用 `st.button` + `st.session_state` 来切换显示状态（点击齿轮 → session_state 翻转 → rerun → 抽屉滑出）。CSS transition 处理动画。

### 5. Welcome 居中

**选择**：将 welcome 内容包裹在 flexbox 容器中，`min-height: 60vh` + `justify-content: center` + `align-items: center`

将 `render_empty_state()` 中所有内容（welcome message + step cards + example queries）包裹在一个外层 div 中，避免内容分散在多个 st 调用中导致居中失效。

## Risks / Trade-offs

1. **[线程安全] Worker 线程写 queue、主线程读 queue 并更新 session_state** → Streamlit 的 session_state 不是线程安全的。缓解方案：worker 线程只写 queue，不直接触碰 session_state；主线程在每次 rerun 开始时消费 queue 并写入 session_state。

2. **[LangGraph cancel 传播] `asyncio.Task.cancel()` 可能无法穿透 LangGraph 内部** → 实施时先做 spike 测试。如果 cancel 信号无法到达，降级为在 graph 各节点入口通过 event_bus 检查 cancel flag。

3. **[Worker 线程生命周期] 如果用户刷新页面或关闭标签，worker 线程仍在运行** → 后端 cancel 端点作为兜底；在 worker 中设置一个合理的最大运行时间。

4. **[Streamlit rerun 循环] 运行中高频 rerun 可能消耗资源** → 使用 `time.sleep(0.1-0.2)` 控制轮询频率；如果有新事件则立即 rerun，否则降低频率。

## Migration Plan

无破坏性变更，无需数据迁移。部署步骤：
1. 部署后端取消端点（向后兼容，不影响现有流程）
2. 部署前端更新（新前端可配合旧后端，停止按钮在无后端取消端点时降级为仅断开 SSE 连接）
3. 无需回滚计划（新旧版本可共存）
