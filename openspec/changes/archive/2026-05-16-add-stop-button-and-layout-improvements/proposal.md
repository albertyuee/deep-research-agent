## Why

当前前端在用户发起研究后 UI 完全阻塞（`asyncio.run()` 占据主线程），无法中途取消正在运行的研究任务。同时页面布局存在几个 UX 问题：空闲时 welcome 区域未在容器内居中、调试面板占据可见侧边栏、运行中缺少状态概览和控制入口。本次改动将取消能力补全，并对前端布局做一次整体打磨。

## What Changes

- **新增停止按钮**：研究运行中在状态栏展示停止按钮，点击后立即终止研究
- **前端异步架构重构**：将 `asyncio.run()` 阻塞模式改为 `threading.Thread` + 轮询模式，保持 UI 可交互
- **后端取消机制**：新增 `POST /api/v1/research/{task_id}/cancel` 端点，支持 `asyncio.Task.cancel()` 立即终止
- **取消状态处理**：取消后保留已生成的部分报告文本和已有的进度数据，页面显示"研究已取消"提示
- **Welcome 居中修复**：空闲状态下隐藏左侧进度面板，welcome 区域在右侧全宽容器中水平和垂直居中
- **调试抽屉**：将侧边栏调试面板改为右侧滑出式 drawer，点击齿轮图标 ⚙️ 展开/收起
- **运行状态栏**：研究运行中在顶部显示状态栏（当前阶段 + 进度条 + 耗时 + 停止按钮）

## Capabilities

### New Capabilities
- `research-cancel`: 用户可立即终止正在运行的研究任务，后端响应 asyncio.Task.cancel()，前端显示取消状态并保留部分结果
- `debug-drawer`: 右侧滑出式调试抽屉面板，包含事件日志、阶段耗时、重试历史，替代原 st.sidebar 实现
- `layout-states`: 前端根据研究状态（idle / running / completed / cancelled）动态调整页面布局（列显隐、状态栏、提示信息）

### Modified Capabilities
<!-- No existing capabilities to modify -->

## Impact

- **后端**: `backend/services/research_service.py`（新增 CANCELLED 状态、存储 task 引用）、`backend/routers/research.py`（新增 cancel 端点、CancelledError 处理）
- **前端核心**: `frontend/app.py`（异步架构重构、动态布局、状态栏）
- **前端组件**: `frontend/components/agent_progress.py`（取消状态）、`frontend/components/empty_state.py`（居中修复）
- **前端样式**: `frontend/static/style.css`（居中、drawer、状态栏样式）
- **新增**: `frontend/components/debug_drawer.py`（调试抽屉组件）
