# Vue 3 前端重设计 — 设计文档

## 概述

将 Deep Research Agent 前端从 Streamlit 迁移到 Vue 3 + Vite + TypeScript，实现更专业的 UI、更好的性能和可扩展性。后端 FastAPI 保持不变。

## 目标

- 用 Vue 3 完全重写前端，去掉 Streamlit
- 替换 `session_state` / `queue.Queue` / `st.rerun()` 轮询为 Vue 响应式系统 + 原生 EventSource
- 保留所有现有功能（搜索、进度展示、报告渲染、来源引用、取消、调试面板）
- 预留扩展性：快速检索、资料上传管理、LLM 提供商设置
- 侧边栏导航布局，Naive UI 组件库

## 技术栈

| 层面 | 选择 | 原因 |
|------|------|------|
| 框架 | Vue 3 (Composition API) + TypeScript | 易于上手，中文文档好，SFC 直观 |
| 构建 | Vite | HMR 极快，Vue 生态标配 |
| 组件库 | Naive UI | 设计感强，Tree-shaking 好，TypeScript 优先 |
| 样式 | Tailwind CSS + Naive UI 内置 | 互补：Tailwind 做布局/间距，Naive 做组件 |
| 状态管理 | Pinia | Vue 官方推荐，类型安全，API 简洁 |
| 路由 | Vue Router 4 | 预留多页面扩展 |
| SSE 客户端 | 原生 `EventSource` | 无需额外依赖，浏览器原生 API |

## 架构

```
Frontend (Vue/Vite, localhost:5173)      Backend (FastAPI, localhost:8000, 不变)
┌──────────────────────────┐            ┌──────────────────────────┐
│ Vue 3 SPA                │  POST      │ /api/v1/research         │
│                          │ ─────────→ │                           │
│ EventSource ─────────────│  SSE       │ /api/v1/research/{id}/stream │
│                          │ ←───────── │                           │
│ fetch ───────────────────│  GET       │ /api/v1/research/{id}    │
│                          │ ←───────── │                           │
│                          │  POST      │ /api/v1/research/{id}/cancel │
│                          │ ─────────→ │                           │
└──────────────────────────┘            └──────────────────────────┘

开发: Vite dev server (5173) → proxy /api → FastAPI (8000)
生产: Vite build → dist/ 静态文件 → FastAPI StaticFiles 或 Nginx
```

## 路由结构

```
/                 → ResearchPage    深度研究（主页）
/quick-search     → QuickSearchPage 快速检索（预留）
/documents        → DocumentsPage   资料管理（预留）
/settings         → SettingsPage    LLM 配置 + 系统设置（预留）
```

## 组件树

```
App.vue
└── AppLayout.vue                    # 侧边栏 + 内容区
    ├── SideNav.vue                  # Naive n-menu 垂直导航
    │   ├── Logo + 标题
    │   ├── Nav items (深度研究, 快速检索, 资料管理, 设置)
    │   └── 可折叠为仅图标模式
    └── <router-view>
        └── ResearchPage.vue         # / 主页
            ├── SearchForm.vue       # 输入框 + 示例 chips + 开始按钮
            ├── AgentStepper.vue     # 四阶段进度指示器（纯 CSS）
            ├── ProgressPanel.vue    # 左侧：Agent 思考过程
            │   ├── ResearchPlanList.vue   # 拆解后的子问题列表
            │   ├── RetrievalDetail.vue    # 检索详情卡片
            │   ├── CritiqueResult.vue     # 质量评估卡片
            │   └── EventTimeline.vue      # 事件时间线（可折叠）
            ├── ReportView.vue       # 右侧：Markdown 报告（marked 渲染）
            └── SourceList.vue       # 引用来源卡片列表
```

## Pinia Store

### research.ts（核心 Store）

```typescript
interface ResearchState {
  // 任务状态
  query: string
  taskId: string | null
  isRunning: boolean
  isCancelled: boolean

  // 报告
  report: string                // 最终报告
  streamingReport: string       // SSE 实时流文本

  // 来源
  sources: Source[]

  // Stepper 状态
  phaseStates: {
    decomposition: PhaseState
    retrieval: PhaseState
    critique: PhaseState
    synthesis: PhaseState
  }

  // 进度
  progressValue: number

  // 详细数据
  researchPlan: PlanItem[]
  critiqueResults: CritiqueItem[]
  retrievalProgress: RetrievalProgress | null
  eventLog: EventLogItem[]
  retryHistory: RetryHistoryItem[]

  // 计时
  startedAt: number | null
  phaseDurations: Record<string, number>
}
```

### settings.ts（预留）
LLM provider、API key、模型选择等配置。

### documents.ts（预留）
上传文件列表、处理状态等。

## SSE 数据流

```
用户提交 → api.submitResearch(query) → POST /api/v1/research → task_id
         → new EventSource(`/api/v1/research/${task_id}/stream`)
         → onmessage 解析 event field → dispatch 到对应 handler
         → handler 直接修改 Pinia Store → Vue 响应式自动更新 UI
```

关键 events 映射：

| SSE Event | Store Action | UI 效果 |
|-----------|-------------|---------|
| research_plan_chunk | addPlanItem() | 研究计划列表追加一项 |
| retrieval_start | updateRetrievalProgress() | 状态栏更新 + stepper 高亮 |
| retrieval_result | setRetrievalResult() | 检索详情卡片更新 |
| critique_result | addCritiqueResult() | 评估卡片 + 分数颜色变化 |
| retry_triggered | triggerRetry() | stepper 回到检索，警告提示 |
| synthesis_chunk | appendReport() | 报告区实时追加 Markdown |
| done | finishResearch() | stepper 全部完成，加载来源 |
| cancelled | cancelResearch() | 停止状态，保留部分结果 |
| error | setError() | 错误提示 |

## 与 Streamlit 版的关键改进

| Streamlit | Vue 3 |
|-----------|-------|
| `st.session_state` 字典 | Pinia Store，类型安全 |
| `queue.Queue` + `threading.Event` | 原生 `EventSource`，无队列 |
| `while running: st.rerun(); sleep(0.15)` | 响应式系统自动更新 |
| `st.empty()` placeholder DOM 管理 | Vue 条件渲染 `v-if`，天然无残留 |
| `st.form` + `st.button` 限制 | 完全自由的组件组合 |
| CSS 通过 `unsafe_allow_html` 注入 | Scoped CSS + Tailwind |
| `asyncio.run()` 在后台线程中 | 不需要，浏览器原生异步 |
| 无法使用 npm 生态 | 完整 npm 生态 |

## 项目结构

```
frontend-vue/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── tailwind.config.js
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   ├── research.ts
│   │   ├── settings.ts
│   │   └── documents.ts
│   ├── composables/
│   │   └── useResearch.ts        # SSE 连接管理
│   ├── api/
│   │   └── research.ts           # HTTP 请求封装
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.vue
│   │   │   └── SideNav.vue
│   │   ├── research/
│   │   │   ├── SearchForm.vue
│   │   │   ├── AgentStepper.vue
│   │   │   ├── ProgressPanel.vue
│   │   │   ├── ResearchPlanList.vue
│   │   │   ├── RetrievalDetail.vue
│   │   │   ├── CritiqueResult.vue
│   │   │   └── EventTimeline.vue
│   │   ├── report/
│   │   │   ├── ReportView.vue
│   │   │   └── SourceList.vue
│   │   └── common/
│   │       └── ScoreBadge.vue
│   ├── pages/
│   │   ├── ResearchPage.vue
│   │   ├── QuickSearchPage.vue
│   │   ├── DocumentsPage.vue
│   │   └── SettingsPage.vue
│   └── styles/
│       ├── main.css              # Tailwind directives
│       └── variables.css         # CSS 变量（主题色等）
└── public/
    └── favicon.svg
```

## 视觉设计

- 主题：延续暖色浅色系，品牌色为紫色调（#7c3aed）
- Naive UI 的 `NMenu`、`NCard`、`NButton`、`NProgress`、`NTag` 等组件
- 自定义 stepper 用纯 CSS/CSS transition（Naive UI 无内建 stepper）
- Markdown 用 `marked` 库渲染，配合 GitHub 风格 CSS
- 响应式：桌面端侧边栏常驻，移动端可折叠

## 不在本次范围内的内容

- 快速检索页面完整实现（仅预留路由和占位页面）
- 资料管理完整实现（仅预留路由和占位页面）
- LLM 设置页面完整实现（仅预留路由和占位页面）
- 后端任何改动
- 暗色模式（后续可用 Naive UI 的 `darkTheme` 快速添加）
- 用户认证
- 历史记录持久化
