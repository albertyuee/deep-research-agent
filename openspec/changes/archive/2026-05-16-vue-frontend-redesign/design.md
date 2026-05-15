# Frontend — Vue 3 SPA

## Architecture

Vue 3 SPA 通过 Vite proxy 与 FastAPI 后端通信。无需 Nuxt/Next，SPA 即可满足需求。

## SSE Data Flow

```
用户提交 → POST /api/v1/research → task_id
         → new EventSource(stream) → onmessage → 解析 JSON
         → store.handleEvent(event_type, data) → Vue 响应式更新 UI
```

## Routes

| Path | Page | Status |
|------|------|--------|
| `/` | ResearchPage | 完成 |
| `/quick-search` | QuickSearchPage | 占位 |
| `/documents` | DocumentsPage | 占位 |
| `/settings` | SettingsPage | 占位 |

## Components

- **SearchForm** — 输入框 + 示例 chips + 开始/停止按钮
- **AgentStepper** — 四阶段进度（拆解→检索→评估→合成）
- **ProgressPanel** — 研究计划、检索详情、质量评估、重试、耗时
- **EventTimeline** — SSE 事件日志表格
- **ReportView** — Markdown 报告渲染（marked）
- **SourceList** — 来源引用卡片（去重）
