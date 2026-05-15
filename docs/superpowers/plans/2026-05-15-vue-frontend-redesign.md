# Vue 3 Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Streamlit frontend as a Vue 3 + Naive UI SPA, preserving all existing features while adding a sidebar navigation layout and placeholder pages for future expansion.

**Architecture:** Vue 3 SPA in `frontend-vue/` communicates with the unchanged FastAPI backend via POST (submit), EventSource (SSE stream), and GET (final result). Vite dev server proxies `/api` to `localhost:8000`. State managed by Pinia stores, SSE events dispatched through a `useResearch` composable.

**Tech Stack:** Vue 3 (Composition API) + TypeScript, Vite, Naive UI, Tailwind CSS, Pinia, Vue Router 4, marked (Markdown)

---

### File Structure

```
frontend-vue/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── tailwind.config.js
├── postcss.config.js
├── env.d.ts
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/index.ts
│   ├── stores/
│   │   ├── research.ts          # Core research state + SSE event handlers
│   │   ├── settings.ts          # LLM config (placeholder)
│   │   └── documents.ts         # File management (placeholder)
│   ├── composables/
│   │   └── useResearch.ts       # SSE connection + lifecycle management
│   ├── api/
│   │   └── research.ts          # HTTP calls (submit, fetch result, cancel)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.vue    # Sidebar + router-view shell
│   │   │   └── SideNav.vue      # Naive n-menu vertical nav
│   │   ├── research/
│   │   │   ├── SearchForm.vue   # Query input + example chips + submit
│   │   │   ├── AgentStepper.vue # 4-phase step indicator (pure CSS)
│   │   │   ├── ProgressPanel.vue# Left panel: plan + retrieval + critique
│   │   │   └── EventTimeline.vue# Collapsible SSE event log table
│   │   ├── report/
│   │   │   ├── ReportView.vue   # Markdown rendering via marked
│   │   │   └── SourceList.vue   # Source citation cards
│   │   └── common/
│   │       └── ScoreBadge.vue   # Color-coded score display
│   ├── pages/
│   │   ├── ResearchPage.vue     # Main deep research page
│   │   ├── QuickSearchPage.vue  # Placeholder
│   │   ├── DocumentsPage.vue    # Placeholder
│   │   └── SettingsPage.vue     # Placeholder
│   └── styles/
│       └── main.css             # Tailwind directives + custom CSS
└── public/
    └── favicon.svg
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `frontend-vue/package.json`
- Create: `frontend-vue/index.html`
- Create: `frontend-vue/vite.config.ts`
- Create: `frontend-vue/tsconfig.json`
- Create: `frontend-vue/tsconfig.app.json`
- Create: `frontend-vue/tsconfig.node.json`
- Create: `frontend-vue/tailwind.config.js`
- Create: `frontend-vue/postcss.config.js`
- Create: `frontend-vue/env.d.ts`
- Create: `frontend-vue/public/favicon.svg`

- [ ] **Step 1: Create the frontend-vue directory and package.json**

```bash
mkdir -p frontend-vue/public frontend-vue/src
```

```json
{
  "name": "deep-research-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.13",
    "vue-router": "^4.5.0",
    "pinia": "^2.3.0",
    "naive-ui": "^2.41.0",
    "@vicons/ionicons5": "^0.12.0",
    "marked": "^15.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.0",
    "typescript": "~5.6.0",
    "vite": "^6.0.0",
    "vue-tsc": "^2.2.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend-vue && npm install
```

- [ ] **Step 3: Create index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Deep Research Agent</title>
    <link rel="icon" href="/favicon.svg" />
  </head>
  <body class="bg-gray-50">
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 4: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 5: Create TypeScript config files**

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForExpose": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue", "env.d.ts"]
}
```

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: Create Tailwind and PostCSS config**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          500: '#a855f7',
          600: '#9333ea',
          700: '#7c3aed',
        },
      },
    },
  },
  plugins: [],
}
```

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 7: Create env.d.ts**

```typescript
/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 8: Create favicon.svg**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <text y=".9em" font-size="90">🔬</text>
</svg>
```

- [ ] **Step 9: Create src/styles/main.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --brand-500: #a855f7;
  --brand-600: #9333ea;
  --brand-700: #7c3aed;
  --success: #18a058;
  --warning: #f0a020;
  --error: #d03050;
}

body {
  font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', -apple-system, sans-serif;
}

/* Stepper */
.stepper { display: flex; align-items: center; justify-content: center; gap: 0; padding: 8px 0; }
.stepper-dot {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; transition: all 0.3s ease; flex-shrink: 0;
}
.stepper-dot.waiting  { background: #e5e7eb; color: #9ca3af; }
.stepper-dot.running  { background: linear-gradient(135deg, #7c3aed, #a78bfa); color: #fff; animation: pulse-dot 1.5s infinite; }
.stepper-dot.complete { background: #18a058; color: #fff; }
.stepper-dot.error    { background: #d03050; color: #fff; }
.stepper-connector { flex: 1; height: 3px; background: #e5e7eb; border-radius: 2px; margin: 0 4px 20px 4px; transition: background 0.3s; }
.stepper-connector.done { background: #18a058; }
.stepper-label { font-size: 0.75rem; color: #6b7280; text-align: center; white-space: nowrap; font-weight: 500; min-width: 50px; }
.stepper-label.active { color: #7c3aed; font-weight: 700; }

@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(124, 58, 237, 0); }
}

/* Score bars */
.score-bar-bg { width: 100%; height: 6px; background: #f3f4f6; border-radius: 3px; overflow: hidden; margin: 6px 0; }
.score-bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.score-bar-fill.pass { background: linear-gradient(90deg, #18a058, #36ad6a); }
.score-bar-fill.warn { background: linear-gradient(90deg, #f0a020, #f2c94c); }
.score-bar-fill.fail { background: linear-gradient(90deg, #d03050, #e88080); }

/* Source cards */
.source-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
  padding: 14px; margin: 10px 0; transition: all 0.2s;
}
.source-card:hover { border-color: #c4b5fd; box-shadow: 0 4px 12px rgba(124, 58, 237, 0.08); }

/* Typing cursor animation */
.typing-cursor { display: inline-block; width: 2px; height: 1em; background: #7c3aed; animation: blink 1s infinite; vertical-align: text-bottom; margin-left: 2px; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f3f4f6; border-radius: 3px; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
```

- [ ] **Step 10: Commit scaffold**

```bash
cd frontend-vue && git add -A && git commit -m "feat: scaffold Vue 3 + Vite + Tailwind + Naive UI project"
```

---

### Task 2: App Shell — main.ts, App.vue, Router, Layout

**Files:**
- Create: `frontend-vue/src/main.ts`
- Create: `frontend-vue/src/App.vue`
- Create: `frontend-vue/src/router/index.ts`
- Create: `frontend-vue/src/components/layout/AppLayout.vue`
- Create: `frontend-vue/src/components/layout/SideNav.vue`

- [ ] **Step 1: Create src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'
import router from './router'
import App from './App.vue'
import './styles/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(naive)
app.mount('#app')
```

- [ ] **Step 2: Create src/App.vue**

```vue
<template>
  <AppLayout />
</template>

<script setup lang="ts">
import AppLayout from '@/components/layout/AppLayout.vue'
</script>
```

- [ ] **Step 3: Create src/router/index.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'research',
      component: () => import('@/pages/ResearchPage.vue'),
    },
    {
      path: '/quick-search',
      name: 'quick-search',
      component: () => import('@/pages/QuickSearchPage.vue'),
    },
    {
      path: '/documents',
      name: 'documents',
      component: () => import('@/pages/DocumentsPage.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/pages/SettingsPage.vue'),
    },
  ],
})

export default router
```

- [ ] **Step 4: Create src/components/layout/AppLayout.vue**

```vue
<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-layout has-sider position="absolute" style="height: 100vh;">
      <SideNav />
      <n-layout-content>
        <div class="p-6 max-w-[1400px] mx-auto">
          <router-view />
        </div>
      </n-layout-content>
    </n-layout>
  </n-config-provider>
</template>

<script setup lang="ts">
import { zhCN, dateZhCN } from 'naive-ui'
import SideNav from './SideNav.vue'

const themeOverrides = {
  common: {
    primaryColor: '#7c3aed',
    primaryColorHover: '#9333ea',
    primaryColorPressed: '#6d28d9',
    primaryColorSuppl: '#a78bfa',
    borderRadius: '10px',
  },
}
</script>
```

- [ ] **Step 5: Create src/components/layout/SideNav.vue**

```vue
<template>
  <n-layout-sider
    bordered
    collapse-mode="width"
    :collapsed-width="64"
    :width="200"
    :collapsed="collapsed"
    show-trigger
    @collapse="collapsed = true"
    @expand="collapsed = false"
  >
    <div class="flex flex-col h-full">
      <div class="p-4 flex items-center gap-2" :class="collapsed ? 'justify-center' : ''">
        <span class="text-2xl">🔬</span>
        <span v-if="!collapsed" class="font-bold text-base text-gray-800 whitespace-nowrap">
          Deep Research
        </span>
      </div>

      <n-menu
        :value="currentRoute"
        :collapsed="collapsed"
        :collapsed-width="64"
        :options="menuOptions"
        @update:value="navigate"
      />

      <div class="mt-auto p-3">
        <n-button
          v-if="!collapsed"
          text
          size="small"
          @click="collapsed = !collapsed"
          class="text-gray-400"
        >
          <template #icon><n-icon><chevron-back /></n-icon></template>
          收起菜单
        </n-button>
      </div>
    </div>
  </n-layout-sider>
</template>

<script setup lang="ts">
import { ref, computed, h, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  SearchOutline, FlashOutline, DocumentTextOutline,
  SettingsOutline, ChevronBack
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

const currentRoute = computed(() => route.path)

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = [
  { label: '深度研究', key: '/', icon: renderIcon(SearchOutline) },
  { label: '快速检索', key: '/quick-search', icon: renderIcon(FlashOutline) },
  { label: '资料管理', key: '/documents', icon: renderIcon(DocumentTextOutline) },
  { label: '系统设置', key: '/settings', icon: renderIcon(SettingsOutline) },
]

function navigate(key: string) {
  router.push(key)
}
</script>
```

- [ ] **Step 6: Verify app starts**

Run: `cd frontend-vue && npm run dev`
Expected: Vite dev server starts on port 5173, app loads with sidebar navigation.

- [ ] **Step 7: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add app shell with sidebar navigation and router"
```

---

### Task 3: Pinia Stores

**Files:**
- Create: `frontend-vue/src/stores/research.ts`
- Create: `frontend-vue/src/stores/settings.ts`
- Create: `frontend-vue/src/stores/documents.ts`

- [ ] **Step 1: Create src/stores/research.ts**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type PhaseState = 'waiting' | 'running' | 'complete' | 'error'

export interface PlanItem {
  index: number
  question: string
  strategy: string
  rationale: string
}

export interface CritiqueItem {
  step: number
  score: number
  relevance: number
  completeness: number
  passed: boolean
  reasoning: string
  retrySuggestion: string
}

export interface RetrievalProgress {
  step: number
  total: number
  strategy: string
  results: number
  topScore: number
  topPreview: string
  retry: number
}

export interface EventLogItem {
  elapsed: number
  eventType: string
  summary: string
  data: Record<string, unknown>
}

export interface RetryHistoryItem {
  attempt: number
  score: number
  suggestion: string
}

export interface Source {
  chunk_id: string
  score: number
  combined_score?: number
  metadata: Record<string, unknown>
  content: string
}

export const useResearchStore = defineStore('research', () => {
  const query = ref('')
  const taskId = ref<string | null>(null)
  const isRunning = ref(false)
  const isCancelled = ref(false)
  const error = ref<string | null>(null)

  const report = ref('')
  const streamingReport = ref('')
  const sources = ref<Source[]>([])

  const phaseStates = ref<Record<string, PhaseState>>({
    decomposition: 'waiting',
    retrieval: 'waiting',
    critique: 'waiting',
    synthesis: 'waiting',
  })

  const progressValue = ref(0)
  const currentDetail = ref('')

  const researchPlan = ref<PlanItem[]>([])
  const critiqueResults = ref<CritiqueItem[]>([])
  const retrievalProgress = ref<RetrievalProgress | null>(null)
  const eventLog = ref<EventLogItem[]>([])
  const retryHistory = ref<RetryHistoryItem[]>([])

  const startedAt = ref<number | null>(null)
  const phaseDurations = ref<Record<string, number>>({})
  const phaseStartTimes = ref<Record<string, number>>({})

  const previousStep = ref('')

  const currentStep = computed(() => {
    if (isCancelled.value) return 'cancelled'
    if (phaseStates.value.synthesis === 'complete') return 'done'
    if (phaseStates.value.synthesis === 'running') return 'synthesizing'
    if (phaseStates.value.critique === 'running') return 'evaluating'
    if (phaseStates.value.retrieval === 'running') return 'retrieving'
    if (phaseStates.value.decomposition === 'running') return 'planning'
    return ''
  })

  const phaseLabels: Record<string, string> = {
    decomposition: '拆解问题',
    retrieval: '检索',
    critique: '评估',
    synthesis: '合成报告',
  }

  function reset() {
    query.value = ''
    taskId.value = null
    isRunning.value = false
    isCancelled.value = false
    error.value = null
    report.value = ''
    streamingReport.value = ''
    sources.value = []
    phaseStates.value = {
      decomposition: 'waiting',
      retrieval: 'waiting',
      critique: 'waiting',
      synthesis: 'waiting',
    }
    progressValue.value = 0
    currentDetail.value = ''
    researchPlan.value = []
    critiqueResults.value = []
    retrievalProgress.value = null
    eventLog.value = []
    retryHistory.value = []
    startedAt.value = null
    phaseDurations.value = {}
    phaseStartTimes.value = {}
    previousStep.value = ''
  }

  function summarizeEvent(eventType: string, data: Record<string, unknown>): string {
    switch (eventType) {
      case 'research_plan_start':
        return `开始拆解: ${(data.query as string || '').slice(0, 60)}`
      case 'research_plan_chunk':
        return `子问题 #${data.index}: ${(data.question as string || '').slice(0, 50)} (策略: ${data.strategy})`
      case 'retrieval_start':
        return `检索 ${data.step}/${data.total} (策略: ${data.strategy})`
      case 'retrieval_result':
        return `检索完成: ${data.result_count} 条结果, top=${(data.top_score as number || 0).toFixed(3)}`
      case 'critique_start':
        return `评估检索质量 (步骤 ${data.step})`
      case 'critique_result': {
        const s = data.composite_score as number || 0
        const p = data.passed ? 'PASS' : 'FAIL'
        return `评估结果: ${s.toFixed(3)} [${p}]`
      }
      case 'retry_triggered':
        return `触发重试 #${data.count}`
      case 'synthesis_start':
        return `开始生成报告 (${data.total_steps} 步骤聚合)`
      case 'synthesis_chunk':
        return `报告片段: ${(data.text as string || '').slice(0, 60)}...`
      case 'done':
        return `完成, 报告长度: ${data.report_length || 0} 字符`
      case 'error':
        return `错误: ${(data.message as string || '').slice(0, 80)}`
      default:
        return eventType
    }
  }

  function estimateProgress(eventType: string): number {
    const estimates: Record<string, number> = {
      'research_plan_start': 0.05,
      'research_plan_chunk': 0.10,
      'retrieval_start': 0.15,
      'retrieval_result': 0.35,
      'critique_start': 0.40,
      'critique_result': 0.50,
      'retry_triggered': 0.35,
      'synthesis_start': 0.60,
      'synthesis_chunk': 0.75,
      'done': 1.0,
      'error': 0,
    }
    return estimates[eventType] ?? progressValue.value
  }

  function recordPhaseTime(key: string) {
    if (key in phaseStartTimes.value) {
      const start = phaseStartTimes.value[key]
      delete phaseStartTimes.value[key]
      phaseDurations.value[key] = (Date.now() - start) / 1000
    }
  }

  function handleEvent(eventType: string, data: Record<string, unknown>) {
    const elapsed = startedAt.value ? (Date.now() - startedAt.value) / 1000 : 0
    const summary = summarizeEvent(eventType, data)
    eventLog.value.push({ elapsed, eventType, summary, data })
    if (eventLog.value.length > 500) {
      eventLog.value = eventLog.value.slice(-500)
    }

    if (typeof data.progress === 'number') {
      progressValue.value = data.progress as number
    } else {
      progressValue.value = estimateProgress(eventType)
    }

    switch (eventType) {
      case 'research_plan_start':
        previousStep.value = currentStep.value
        currentDetail.value = '正在拆解研究问题...'
        researchPlan.value = []
        startedAt.value = Date.now()
        eventLog.value = []
        phaseDurations.value = {}
        retryHistory.value = []
        phaseStates.value = {
          decomposition: 'running',
          retrieval: 'waiting',
          critique: 'waiting',
          synthesis: 'waiting',
        }
        phaseStartTimes.value['decomposition'] = Date.now()
        progressValue.value = 0.05
        break

      case 'research_plan_chunk':
        researchPlan.value.push({
          index: data.index as number,
          question: data.question as string,
          strategy: data.strategy as string,
          rationale: data.rationale as string || '',
        })
        recordPhaseTime('decomposition')
        phaseStates.value.decomposition = 'complete'
        break

      case 'retrieval_start': {
        previousStep.value = currentStep.value
        const step = data.step as number
        const total = data.total as number
        const strategyName: Record<string, string> = {
          semantic: '语义', keyword: '关键词', hybrid: '混合'
        }
        const strategyLabel = strategyName[data.strategy as string] || (data.strategy as string)
        currentDetail.value = `正在检索 子问题 ${step}/${total}（${strategyLabel}策略）`
        retrievalProgress.value = {
          step, total,
          strategy: data.strategy as string,
          results: 0, topScore: 0, topPreview: '',
          retry: (data.retry_count as number) || 0,
        }
        phaseStartTimes.value[`retrieval_${step}`] = Date.now()
        phaseStates.value.retrieval = 'running'
        break
      }

      case 'retrieval_result': {
        const rp = retrievalProgress.value
        if (rp) {
          rp.results = data.result_count as number
          rp.topScore = data.top_score as number
          rp.topPreview = data.top_preview as string || ''
        }
        currentDetail.value = `检索完成，找到 ${data.result_count} 条结果（最高相似度: ${(data.top_score as number || 0).toFixed(2)}）`
        recordPhaseTime(`retrieval_${data.step}`)
        break
      }

      case 'critique_start':
        previousStep.value = currentStep.value
        currentDetail.value = '正在评估检索质量...'
        phaseStartTimes.value['critique'] = Date.now()
        phaseStates.value.retrieval = 'complete'
        phaseStates.value.critique = 'running'
        break

      case 'critique_result': {
        const passed = data.passed as boolean
        critiqueResults.value.push({
          step: data.step as number,
          score: data.composite_score as number,
          relevance: data.relevance as number,
          completeness: data.completeness as number,
          passed,
          reasoning: data.reasoning as string || '',
          retrySuggestion: data.retry_suggestion as string || '',
        })
        currentDetail.value = `质量评估: ${(data.composite_score as number).toFixed(2)} 分 — ${passed ? '通过' : '不通过'}`
        recordPhaseTime('critique')
        phaseStates.value.critique = 'complete'
        phaseStates.value.synthesis = passed ? 'running' : 'waiting'
        break
      }

      case 'retry_triggered': {
        previousStep.value = currentStep.value
        const count = data.count as number
        currentDetail.value = `检索质量不达标，正在第 ${count} 次重试（改写查询）...`
        const lastCritique = critiqueResults.value[critiqueResults.value.length - 1]
        retryHistory.value.push({
          attempt: count,
          score: lastCritique?.score ?? 0,
          suggestion: lastCritique?.retrySuggestion ?? '',
        })
        phaseStates.value.critique = 'complete'
        phaseStates.value.retrieval = 'running'
        phaseStates.value.synthesis = 'waiting'
        break
      }

      case 'synthesis_start':
        previousStep.value = currentStep.value
        currentDetail.value = '正在聚合多源信息，生成研究报告...'
        phaseStartTimes.value['synthesis'] = Date.now()
        phaseStates.value.critique = 'complete'
        phaseStates.value.synthesis = 'running'
        break

      case 'synthesis_chunk':
        streamingReport.value += (data.text as string || '')
        break

      case 'done':
        phaseStates.value.synthesis = 'complete'
        progressValue.value = 1.0
        currentDetail.value = `研究完成，报告共 ${data.report_length || 0} 字符`
        recordPhaseTime('synthesis')
        if (streamingReport.value && !report.value) {
          report.value = streamingReport.value
        }
        isRunning.value = false
        break

      case 'error':
        error.value = data.message as string || '发生未知错误'
        markCurrentPhaseError()
        isRunning.value = false
        break

      case 'cancelled':
        isCancelled.value = true
        isRunning.value = false
        markCurrentPhaseError()
        if (streamingReport.value && !report.value) {
          report.value = streamingReport.value
        }
        break
    }
  }

  function markCurrentPhaseError() {
    const phaseMap: Record<string, string> = {
      planning: 'decomposition',
      retrieving: 'retrieval',
      evaluating: 'critique',
      synthesizing: 'synthesis',
    }
    const phaseKey = phaseMap[previousStep.value]
    if (phaseKey) {
      phaseStates.value[phaseKey] = 'error'
    }
  }

  function setQuery(q: string) {
    query.value = q
  }

  function startResearch(tid: string) {
    taskId.value = tid
    isRunning.value = true
    isCancelled.value = false
    error.value = null
    report.value = ''
    streamingReport.value = ''
    sources.value = []
  }

  function setSources(s: Source[]) {
    sources.value = s
  }

  function setFinalReport(text: string, srcs: Source[]) {
    report.value = text
    sources.value = srcs
  }

  return {
    query, taskId, isRunning, isCancelled, error,
    report, streamingReport, sources,
    phaseStates, progressValue, currentDetail,
    researchPlan, critiqueResults, retrievalProgress, eventLog, retryHistory,
    startedAt, phaseDurations, phaseStartTimes, previousStep,
    currentStep, phaseLabels,
    reset, handleEvent, setQuery, startResearch, setSources, setFinalReport,
  }
})
```

- [ ] **Step 2: Create src/stores/settings.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  const llmProvider = ref('siliconflow')
  const apiKey = ref('')
  const model = ref('')

  return { llmProvider, apiKey, model }
})
```

- [ ] **Step 3: Create src/stores/documents.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface DocFile {
  name: string
  size: number
  status: 'uploading' | 'processing' | 'ready' | 'error'
}

export const useDocumentsStore = defineStore('documents', () => {
  const files = ref<DocFile[]>([])

  return { files }
})
```

- [ ] **Step 4: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add Pinia stores (research, settings, documents)"
```

---

### Task 4: API Layer and useResearch Composable

**Files:**
- Create: `frontend-vue/src/api/research.ts`
- Create: `frontend-vue/src/composables/useResearch.ts`

- [ ] **Step 1: Create src/api/research.ts**

```typescript
const BASE = '/api/v1'

export interface TaskResponse {
  success: boolean
  data: {
    task_id: string
    query?: string
    status?: string
    result?: {
      report: string
      sources: Array<{
        chunk_id: string
        score: number
        metadata: Record<string, unknown>
        content: string
      }>
    }
    error?: string
  }
  error: string | null
}

export async function submitResearch(query: string): Promise<string> {
  const resp = await fetch(`${BASE}/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!resp.ok) {
    throw new Error(`提交失败: ${resp.status} ${resp.statusText}`)
  }
  const body: TaskResponse = await resp.json()
  if (!body.success || !body.data?.task_id) {
    throw new Error(body.error || '提交失败：未获取到任务 ID')
  }
  return body.data.task_id
}

export async function fetchResult(taskId: string): Promise<TaskResponse['data']['result'] | null> {
  const resp = await fetch(`${BASE}/research/${taskId}`)
  if (!resp.ok) return null
  const body: TaskResponse = await resp.json()
  return body.data?.result ?? null
}

export async function cancelResearch(taskId: string): Promise<void> {
  await fetch(`${BASE}/research/${taskId}/cancel`, { method: 'POST' })
}
```

- [ ] **Step 2: Create src/composables/useResearch.ts**

```typescript
import { useResearchStore } from '@/stores/research'
import { submitResearch, fetchResult, cancelResearch } from '@/api/research'

export function useResearch() {
  const store = useResearchStore()
  let eventSource: EventSource | null = null

  async function start(query: string): Promise<void> {
    store.reset()
    store.setQuery(query)

    try {
      const taskId = await submitResearch(query)
      store.startResearch(taskId)

      eventSource = new EventSource(`/api/v1/research/${taskId}/stream`)

      eventSource.onmessage = (e: MessageEvent) => {
        try {
          const payload = JSON.parse(e.data)
          const eventType = payload.event
          const eventData = payload.data || {}
          store.handleEvent(eventType, eventData)

          if (eventType === 'done' || eventType === 'error' || eventType === 'cancelled') {
            eventSource?.close()
            eventSource = null

            if (eventType === 'done') {
              fetchFinalResult(taskId)
            }
          }
        } catch {
          // Skip malformed events
        }
      }

      eventSource.onerror = () => {
        if (eventSource) {
          store.error = 'SSE 连接中断'
          store.isRunning = false
          eventSource.close()
          eventSource = null
        }
      }
    } catch (e) {
      store.error = e instanceof Error ? e.message : '连接后端失败'
      store.isRunning = false
    }
  }

  async function stop(): Promise<void> {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    if (store.taskId) {
      try {
        await cancelResearch(store.taskId)
      } catch {
        // Best effort
      }
    }
    store.isRunning = false
    store.isCancelled = true
    if (store.streamingReport && !store.report) {
      store.report = store.streamingReport
    }
  }

  async function fetchFinalResult(taskId: string): Promise<void> {
    try {
      const result = await fetchResult(taskId)
      if (result) {
        store.setFinalReport(
          result.report || store.report,
          result.sources || store.sources,
        )
      }
    } catch {
      if (store.streamingReport && !store.report) {
        store.report = store.streamingReport
      }
    }
  }

  function cleanup(): void {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  return { start, stop, cleanup }
}
```

- [ ] **Step 3: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add API layer and useResearch SSE composable"
```

---

### Task 5: SearchForm Component

**Files:**
- Create: `frontend-vue/src/components/research/SearchForm.vue`

- [ ] **Step 1: Create src/components/research/SearchForm.vue**

```vue
<template>
  <div class="mb-5">
    <n-card :bordered="false" class="search-card">
      <n-input
        v-model:value="inputText"
        type="textarea"
        placeholder="输入你的研究问题，例如：人工智能在医疗影像和药物研发中的应用有什么区别？"
        :autosize="{ minRows: 2, maxRows: 4 }"
        :disabled="isRunning"
        size="large"
        round
        @keydown.enter.ctrl="emitSubmit"
      />
      <div class="flex items-center gap-3 mt-3">
        <n-button
          type="primary"
          size="large"
          :disabled="!inputText.trim() || isRunning"
          :loading="isRunning"
          @click="emitSubmit"
        >
          <template #icon><n-icon><rocket-outline /></n-icon></template>
          {{ isRunning ? '研究中...' : '开始研究' }}
        </n-button>
        <n-button
          v-if="isRunning"
          type="error"
          size="large"
          secondary
          @click="$emit('stop')"
        >
          <template #icon><n-icon><stop-circle-outline /></n-icon></template>
          停止
        </n-button>
      </div>

      <div v-if="!isRunning" class="flex flex-wrap gap-2 mt-3">
        <n-tag
          v-for="(ex, i) in examples"
          :key="i"
          :bordered="true"
          type="info"
          size="small"
          class="cursor-pointer hover:border-brand-700 hover:text-brand-700 transition-colors"
          @click="selectExample(ex)"
        >
          {{ ex.slice(0, 35) }}{{ ex.length > 35 ? '…' : '' }}
        </n-tag>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NIcon } from 'naive-ui'
import { RocketOutline, StopCircleOutline } from '@vicons/ionicons5'

const props = defineProps<{
  isRunning: boolean
}>()

const emit = defineEmits<{
  submit: [query: string]
  stop: []
}>()

const examples = [
  '人工智能在医疗影像和药物研发中的应用有什么区别？',
  'Transformer架构相比LSTM在自然语言处理中有哪些优势？',
  '量子计算的发展对现代密码学构成多大的威胁？',
  'CRISPR基因编辑技术在遗传病治疗中的前景和伦理挑战是什么？',
  '固态电池技术相比传统锂电池的核心突破点在哪里？',
]

const inputText = ref(examples[0])

function emitSubmit() {
  const q = inputText.value.trim()
  if (q) {
    emit('submit', q)
  }
}

function selectExample(text: string) {
  inputText.value = text
}
</script>

<style scoped>
.search-card {
  background: linear-gradient(135deg, #ffffff 0%, #fafbff 100%);
  border-radius: 16px;
  box-shadow: 0 2px 16px rgba(124, 58, 237, 0.06);
}
.cursor-pointer {
  cursor: pointer;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add SearchForm component with example chips"
```

---

### Task 6: AgentStepper and ScoreBadge Components

**Files:**
- Create: `frontend-vue/src/components/research/AgentStepper.vue`
- Create: `frontend-vue/src/components/common/ScoreBadge.vue`

- [ ] **Step 1: Create src/components/common/ScoreBadge.vue**

```vue
<template>
  <span class="score-badge" :class="colorClass">{{ score.toFixed(2) }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ score: number }>()

const colorClass = computed(() => {
  if (props.score >= 0.7) return 'pass'
  if (props.score >= 0.4) return 'warn'
  return 'fail'
})
</script>

<style scoped>
.score-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}
.score-badge.pass { background: #d1fae5; color: #065f46; }
.score-badge.warn { background: #fef3c7; color: #92400e; }
.score-badge.fail { background: #fee2e2; color: #991b1b; }
</style>
```

- [ ] **Step 2: Create src/components/research/AgentStepper.vue**

```vue
<template>
  <n-card :bordered="false" size="small" class="mb-4 stepper-card">
    <div class="stepper">
      <template v-for="(key, i) in keys" :key="key">
        <div class="stepper-step">
          <div class="stepper-dot" :class="phaseStates[key]">
            {{ dotIcon(key) }}
          </div>
          <span class="stepper-label" :class="{ active: phaseStates[key] !== 'waiting' }">
            {{ store.phaseLabels[key] }}
          </span>
        </div>
        <div
          v-if="i < keys.length - 1"
          class="stepper-connector"
          :class="{ done: phaseStates[key] === 'complete' }"
        />
      </template>
    </div>

    <!-- Current status -->
    <div v-if="store.currentDetail" class="mt-2">
      <n-alert
        v-if="store.isCancelled"
        type="warning"
        :bordered="false"
      >
        {{ store.currentDetail }}
      </n-alert>
      <n-alert
        v-else-if="store.error"
        type="error"
        :bordered="false"
      >
        {{ store.error }}
      </n-alert>
      <n-alert
        v-else-if="store.currentStep === 'done'"
        type="success"
        :bordered="false"
      >
        {{ store.currentDetail }}
      </n-alert>
      <n-alert
        v-else
        type="info"
        :bordered="false"
      >
        {{ store.currentDetail }}
      </n-alert>
    </div>

    <!-- Progress bar -->
    <n-progress
      v-if="store.currentStep && store.currentStep !== 'done'"
      class="mt-3"
      type="line"
      :percentage="Math.round(Math.min(store.progressValue * 100, 98))"
      :indicator-placement="'inside'"
      :height="20"
      :border-radius="4"
      processing
    />
    <n-progress
      v-else-if="store.currentStep === 'done'"
      class="mt-3"
      type="line"
      :percentage="100"
      status="success"
      :indicator-placement="'inside'"
      :height="20"
      :border-radius="4"
    />

    <!-- Elapsed time -->
    <div v-if="store.startedAt && store.isRunning" class="text-xs text-gray-400 mt-1">
      已用时: {{ elapsedSeconds }}s
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useResearchStore } from '@/stores/research'

const store = useResearchStore()
const keys = ['decomposition', 'retrieval', 'critique', 'synthesis']

const elapsedSeconds = computed(() => {
  if (!store.startedAt) return 0
  return Math.floor((Date.now() - store.startedAt) / 1000)
})

function dotIcon(key: string): string {
  const state = store.phaseStates[key]
  if (state === 'complete') return '✓'
  if (state === 'error') return '✗'
  const iconMap: Record<string, string> = {
    decomposition: '1',
    retrieval: '2',
    critique: '3',
    synthesis: '4',
  }
  return iconMap[key] || '?'
}
</script>

<style scoped>
.stepper-card {
  background: linear-gradient(135deg, #f8fafc 0%, #f5f3ff 100%);
  border-radius: 14px;
  border: 1px solid #ede9fe;
}
</style>
```

- [ ] **Step 3: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add AgentStepper and ScoreBadge components"
```

---

### Task 7: ProgressPanel Component

**Files:**
- Create: `frontend-vue/src/components/research/ProgressPanel.vue`

This component integrates the research plan, retrieval details, critique results, retry history, and timing stats into the left panel.

- [ ] **Step 1: Create src/components/research/ProgressPanel.vue**

```vue
<template>
  <div class="flex flex-col gap-3">
    <!-- Research Plan -->
    <n-card v-if="store.researchPlan.length" title="研究计划" size="small" :bordered="false">
      <template #header-extra>
        <n-tag size="small" type="info">{{ store.researchPlan.length }} 个子问题</n-tag>
      </template>
      <div v-for="p in store.researchPlan" :key="p.index" class="mb-2 pb-2 border-b border-gray-100 last:border-0">
        <div class="flex items-center gap-2">
          <span class="text-sm font-semibold text-gray-700">
            {{ strategyIcon(p.strategy) }} {{ p.index }}. {{ p.question }}
          </span>
          <n-tag :bordered="true" size="tiny">{{ p.strategy }}</n-tag>
        </div>
        <div v-if="p.rationale" class="text-xs text-gray-400 mt-1">
          {{ p.rationale }}
        </div>
      </div>
    </n-card>

    <!-- Retrieval Detail -->
    <n-card v-if="store.retrievalProgress" title="检索详情" size="small" :bordered="false">
      <div class="text-sm space-y-1">
        <div><strong>步骤:</strong> {{ store.retrievalProgress.step }}/{{ store.retrievalProgress.total }}</div>
        <div><strong>策略:</strong> {{ store.retrievalProgress.strategy }}</div>
        <div v-if="store.retrievalProgress.results > 0">
          <strong>结果:</strong> {{ store.retrievalProgress.results }} 条 |
          <strong>相似度:</strong> <ScoreBadge :score="store.retrievalProgress.topScore" />
        </div>
        <div v-if="store.retrievalProgress.retry > 0" class="text-amber-600">
          已重试 {{ store.retrievalProgress.retry }} 次
        </div>
        <!-- Score bar -->
        <div v-if="store.retrievalProgress.topScore > 0" class="score-bar-bg">
          <div
            class="score-bar-fill"
            :class="scoreBarClass(store.retrievalProgress.topScore)"
            :style="{ width: `${Math.min(store.retrievalProgress.topScore * 100, 100)}%` }"
          />
        </div>
        <div v-if="store.retrievalProgress.topPreview" class="text-xs text-gray-400 mt-2 p-2 bg-gray-50 rounded-lg">
          {{ store.retrievalProgress.topPreview.slice(0, 200) }}
        </div>
      </div>
    </n-card>

    <!-- Critique Results -->
    <n-card v-if="store.critiqueResults.length" title="质量评估" size="small" :bordered="false">
      <div v-for="c in store.critiqueResults" :key="c.step" class="mb-3 last:mb-0">
        <div class="flex items-center gap-2 mb-1">
          <n-tag :type="c.passed ? 'success' : 'warning'" size="small">
            {{ c.passed ? '✓ PASS' : '⚠ FAIL' }}
          </n-tag>
          <span class="text-sm text-gray-600">步骤 {{ c.step }}</span>
        </div>
        <div class="text-sm space-y-1 ml-1">
          <div>
            综合 <ScoreBadge :score="c.score" />
            （相关性 {{ c.relevance.toFixed(2) }} / 完整性 {{ c.completeness.toFixed(2) }}）
          </div>
          <div class="score-bar-bg">
            <div class="score-bar-fill" :class="scoreBarClass(c.score)"
              :style="{ width: `${Math.min(c.score * 100, 100)}%` }" />
          </div>
          <div v-if="c.reasoning" class="text-xs text-gray-400 p-2 bg-gray-50 rounded-lg">
            {{ c.reasoning }}
          </div>
          <div v-if="!c.passed && c.retrySuggestion" class="text-xs text-amber-600">
            💡 建议: {{ c.retrySuggestion }}
          </div>
        </div>
      </div>
    </n-card>

    <!-- Retry History -->
    <n-card v-if="store.retryHistory.length" title="重试历史" size="small" :bordered="false">
      <div v-for="h in store.retryHistory" :key="h.attempt" class="text-sm mb-1">
        <strong>第 {{ h.attempt }} 次:</strong>
        上次评分 <ScoreBadge :score="h.score" />
        <span v-if="h.suggestion" class="text-xs text-gray-400"> — {{ h.suggestion }}</span>
      </div>
    </n-card>

    <!-- Timing Stats -->
    <n-card v-if="Object.keys(store.phaseDurations).length" title="阶段耗时" size="small" :bordered="false">
      <div v-for="(dur, key) in store.phaseDurations" :key="key" class="flex justify-between text-sm mb-1">
        <span class="text-gray-600">{{ timingLabel(key) }}</span>
        <span class="text-gray-800 font-medium">{{ dur.toFixed(1) }}s</span>
      </div>
      <n-divider style="margin: 8px 0" />
      <div class="flex justify-between text-sm">
        <span class="text-gray-600">累计</span>
        <span class="text-gray-800 font-semibold">{{ totalTime.toFixed(1) }}s</span>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useResearchStore } from '@/stores/research'
import ScoreBadge from '@/components/common/ScoreBadge.vue'

const store = useResearchStore()

const totalTime = computed(() => {
  return Object.values(store.phaseDurations).reduce((a, b) => a + b, 0)
})

const strategyIconMap: Record<string, string> = {
  semantic: '🧠',
  keyword: '🔑',
  hybrid: '🔀',
}

function strategyIcon(strategy: string): string {
  return strategyIconMap[strategy] || '❓'
}

function scoreBarClass(score: number): string {
  if (score >= 0.7) return 'pass'
  if (score >= 0.4) return 'warn'
  return 'fail'
}

const timingLabelMap: Record<string, string> = {
  decomposition: '拆解问题',
  evaluation: '质量评估',
  synthesis: '合成报告',
}

function timingLabel(key: string): string {
  return timingLabelMap[key] || key.replace('retrieval_', '检索步骤 ')
}
</script>
```

- [ ] **Step 2: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add ProgressPanel with plan, retrieval, critique, and timing"
```

---

### Task 8: EventTimeline Component

**Files:**
- Create: `frontend-vue/src/components/research/EventTimeline.vue`

- [ ] **Step 1: Create src/components/research/EventTimeline.vue**

```vue
<template>
  <n-card v-if="store.eventLog.length" title="事件日志" size="small" :bordered="false">
    <template #header-extra>
      <n-tag size="small">{{ store.eventLog.length }} 条</n-tag>
    </template>
    <div class="max-h-64 overflow-y-auto">
      <n-table :single-line="true" size="small" :bordered="false">
        <thead>
          <tr><th style="width:60px">时间</th><th style="width:180px">事件</th><th>摘要</th></tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in recentEvents" :key="i">
            <td class="text-xs text-gray-400">{{ r.elapsed.toFixed(1) }}s</td>
            <td class="text-xs"><n-tag size="tiny" :bordered="true">{{ r.eventType }}</n-tag></td>
            <td class="text-xs text-gray-600">{{ r.summary }}</td>
          </tr>
        </tbody>
      </n-table>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useResearchStore } from '@/stores/research'

const store = useResearchStore()

const recentEvents = computed(() => store.eventLog.slice(-50))
</script>
```

- [ ] **Step 2: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add EventTimeline component"
```

---

### Task 9: ReportView and SourceList Components

**Files:**
- Create: `frontend-vue/src/components/report/ReportView.vue`
- Create: `frontend-vue/src/components/report/SourceList.vue`

- [ ] **Step 1: Create src/components/report/ReportView.vue**

```vue
<template>
  <div class="report-container">
    <div v-if="!hasContent && !isStreaming" class="flex flex-col items-center justify-center py-20 text-gray-400">
      <span class="text-4xl mb-3">📊</span>
      <p class="text-sm">{{ isRunning ? 'Agent 正在准备报告...' : '输入研究问题开始深度研究' }}</p>
      <div v-if="isRunning" class="typing-cursor mt-1" />
    </div>
    <div v-else-if="isStreaming && !finalReport" class="report-content-wrapper relative">
      <div class="markdown-body" v-html="renderedStreaming" />
      <div class="typing-cursor" />
      <div class="text-xs text-gray-400 mt-2">正在生成中...</div>
    </div>
    <div v-else class="report-content-wrapper">
      <div class="markdown-body" v-html="renderedReport" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  report: string
  streamingReport: string
  isRunning: boolean
}>()

const hasContent = computed(() => props.report || props.streamingReport)
const isStreaming = computed(() => props.isRunning && props.streamingReport)
const finalReport = computed(() => props.report)

const renderedReport = computed(() => {
  if (!props.report) return ''
  return marked.parse(props.report) as string
})

const renderedStreaming = computed(() => {
  if (!props.streamingReport) return ''
  return marked.parse(props.streamingReport) as string
})
</script>

<style scoped>
.report-container {
  min-height: 300px;
}

.report-content-wrapper :deep(.markdown-body) {
  font-size: 0.925rem;
  line-height: 1.75;
  color: #374151;
}

.report-content-wrapper :deep(.markdown-body h1) { font-size: 1.5rem; font-weight: 700; color: #1f2937; margin: 1.5em 0 0.5em; }
.report-content-wrapper :deep(.markdown-body h2) { font-size: 1.25rem; font-weight: 600; color: #374151; margin: 1.25em 0 0.4em; border-bottom: 1px solid #f3f4f6; padding-bottom: 0.3em; }
.report-content-wrapper :deep(.markdown-body h3) { font-size: 1.1rem; font-weight: 600; color: #4b5563; margin: 1em 0 0.3em; }
.report-content-wrapper :deep(.markdown-body p) { margin: 0.6em 0; }
.report-content-wrapper :deep(.markdown-body ul), .report-content-wrapper :deep(.markdown-body ol) { padding-left: 1.5em; }
.report-content-wrapper :deep(.markdown-body li) { margin: 0.3em 0; }
.report-content-wrapper :deep(.markdown-body code) {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.85em;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
.report-content-wrapper :deep(.markdown-body pre) {
  background: #1f2937;
  color: #e5e7eb;
  padding: 16px;
  border-radius: 10px;
  overflow-x: auto;
  font-size: 0.85rem;
}
.report-content-wrapper :deep(.markdown-body blockquote) {
  border-left: 3px solid #c4b5fd;
  padding-left: 14px;
  color: #6b7280;
  margin: 0.8em 0;
}
.report-content-wrapper :deep(.markdown-body table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.8em 0;
}
.report-content-wrapper :deep(.markdown-body th), .report-content-wrapper :deep(.markdown-body td) {
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  text-align: left;
}
.report-content-wrapper :deep(.markdown-body th) {
  background: #f9fafb;
  font-weight: 600;
}
.report-content-wrapper :deep(.markdown-body a) {
  color: #7c3aed;
  text-decoration: underline;
}
</style>
```

- [ ] **Step 2: Create src/components/report/SourceList.vue**

```vue
<template>
  <div v-if="sources.length" class="mt-4">
    <n-divider />
    <h3 class="text-base font-semibold text-gray-700 mb-3">📎 引用来源 ({{ uniqueSources.length }})</h3>
    <div v-for="src in uniqueSources" :key="src.chunk_id" class="source-card">
      <div class="flex items-center gap-2 justify-between flex-wrap">
        <span class="font-semibold text-sm text-gray-800">
          {{ src.metadata?.doc_title || src.metadata?.source || src.chunk_id }}
        </span>
        <div class="flex items-center gap-2">
          <ScoreBadge :score="src.score" />
          <span class="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
            {{ src.metadata?.strategy || 'unknown' }}
          </span>
        </div>
      </div>
      <p class="text-xs text-gray-500 mt-2 line-clamp-3">
        {{ src.content?.slice(0, 200) }}{{ src.content?.length > 200 ? '...' : '' }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ScoreBadge from '@/components/common/ScoreBadge.vue'
import type { Source } from '@/stores/research'

const props = defineProps<{
  sources: Source[]
}>()

const uniqueSources = computed(() => {
  const seen = new Set<string>()
  return props.sources.filter(s => {
    const id = s.chunk_id
    if (seen.has(id)) return false
    seen.add(id)
    return true
  })
})
</script>
```

- [ ] **Step 3: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add ReportView and SourceList components"
```

---

### Task 10: ResearchPage — Wire Everything Together

**Files:**
- Create: `frontend-vue/src/pages/ResearchPage.vue`

- [ ] **Step 1: Create src/pages/ResearchPage.vue**

```vue
<template>
  <div>
    <!-- Page Header -->
    <div class="text-center mb-6">
      <h1 class="text-2xl font-bold bg-gradient-to-r from-brand-700 via-purple-500 to-pink-500 bg-clip-text text-transparent">
        🔬 Deep Research Agent
      </h1>
      <p class="text-sm text-gray-400 mt-1">
        Agentic RAG — 自主拆解问题 · 自适应检索 · 质量评估 · 报告合成
      </p>
    </div>

    <!-- Search Form -->
    <SearchForm
      :is-running="store.isRunning"
      @submit="onSubmit"
      @stop="onStop"
    />

    <!-- Content Area: Two Columns -->
    <div v-if="showContent" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- Left: Agent Progress -->
      <div class="lg:col-span-1">
        <AgentStepper />
        <ProgressPanel />
        <EventTimeline />
      </div>

      <!-- Right: Report -->
      <div class="lg:col-span-2">
        <n-card title="研究报告" size="small" :bordered="false" class="report-panel">
          <ReportView
            :report="store.report"
            :streaming-report="store.streamingReport"
            :is-running="store.isRunning"
          />
        </n-card>
        <SourceList :sources="store.sources" />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="flex flex-col items-center justify-center py-16 text-center">
      <div class="text-6xl mb-4">🔬</div>
      <h2 class="text-xl font-bold text-gray-700 mb-2">欢迎使用 Deep Research Agent</h2>
      <p class="text-gray-400 max-w-md">
        基于 Agentic RAG 的自主深度研究助手<br>
        Agent 自动拆解问题 · 自适应检索 · 评估质量 · 合成报告
      </p>
      <div class="flex gap-4 mt-8">
        <div v-for="(step, i) in steps" :key="i" class="text-center px-4">
          <div class="w-10 h-10 rounded-full bg-gradient-to-br from-brand-700 to-purple-400 text-white flex items-center justify-center mx-auto mb-2 font-bold text-sm">
            {{ i + 1 }}
          </div>
          <div class="text-sm font-semibold text-gray-700">{{ step.title }}</div>
          <div class="text-xs text-gray-400">{{ step.desc }}</div>
        </div>
      </div>
    </div>

    <!-- Cancelled Notice -->
    <n-alert
      v-if="store.isCancelled"
      type="warning"
      :bordered="false"
      class="mt-3"
      title="研究已被取消"
    >
      已保留部分结果。
    </n-alert>

    <!-- Backend Error -->
    <n-alert
      v-if="store.error && !store.isRunning"
      type="error"
      :bordered="false"
      class="mt-3"
      title="后端错误"
    >
      {{ store.error }}
      <template #footer>请确保后端已启动: <code class="bg-gray-100 px-1 rounded">uvicorn backend.main:app --reload</code></template>
    </n-alert>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount } from 'vue'
import { useResearchStore } from '@/stores/research'
import { useResearch } from '@/composables/useResearch'
import SearchForm from '@/components/research/SearchForm.vue'
import AgentStepper from '@/components/research/AgentStepper.vue'
import ProgressPanel from '@/components/research/ProgressPanel.vue'
import EventTimeline from '@/components/research/EventTimeline.vue'
import ReportView from '@/components/report/ReportView.vue'
import SourceList from '@/components/report/SourceList.vue'

const store = useResearchStore()
const { start, stop, cleanup } = useResearch()

const showContent = computed(() => {
  return store.isRunning || store.isCancelled || store.report || store.streamingReport
})

const steps = [
  { title: '输入问题', desc: '输入你想研究的任何问题' },
  { title: 'Agent 研究', desc: '自动拆解→检索→评估→合成' },
  { title: '获取报告', desc: '结构化报告 + 可追溯来源' },
]

async function onSubmit(query: string) {
  await start(query)
}

async function onStop() {
  await stop()
}

onBeforeUnmount(() => {
  cleanup()
})
</script>

<style scoped>
.report-panel {
  min-height: 400px;
  background: #fff;
  border-radius: 14px;
  border: 1px solid #f3f4f6;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add ResearchPage wiring all components together"
```

---

### Task 11: Placeholder Pages

**Files:**
- Create: `frontend-vue/src/pages/QuickSearchPage.vue`
- Create: `frontend-vue/src/pages/DocumentsPage.vue`
- Create: `frontend-vue/src/pages/SettingsPage.vue`

- [ ] **Step 1: Create placeholder pages**

```vue
<!-- QuickSearchPage.vue -->
<template>
  <n-card title="快速检索" :bordered="false">
    <n-result
      status="info"
      title="即将推出"
      description="快速检索功能正在开发中，敬请期待。"
    />
  </n-card>
</template>
```

```vue
<!-- DocumentsPage.vue -->
<template>
  <n-card title="资料管理" :bordered="false">
    <n-result
      status="info"
      title="即将推出"
      description="资料上传和管理功能正在开发中，敬请期待。"
    />
  </n-card>
</template>
```

```vue
<!-- SettingsPage.vue -->
<template>
  <n-card title="系统设置" :bordered="false">
    <n-result
      status="info"
      title="即将推出"
      description="LLM 提供商配置和系统设置正在开发中，敬请期待。"
    />
  </n-card>
</template>
```

All three use the same script setup:
```typescript
<script setup lang="ts">
// Placeholder — will be implemented in future iterations
</script>
```

- [ ] **Step 2: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add placeholder pages for future routes"
```

---

### Task 12: Integration Test with Backend

**Files:**
- Verify: `frontend-vue/src/` (all files exist and compile)

- [ ] **Step 1: Verify TypeScript compilation**

```bash
cd frontend-vue && npx vue-tsc --noEmit
```
Expected: No type errors.

- [ ] **Step 2: Start backend and verify connectivity**

```bash
# Terminal 1: Start backend
cd /Users/albert/Desktop/Ai/测试/deep-research-agent
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend-vue && npm run dev
```

- [ ] **Step 3: Manual integration test**

Open `http://localhost:5173` and verify:

1. Sidebar navigation shows 4 items, clicking navigates to each page.
2. Empty state renders on `/` with the three-step guide.
3. Typing a query in the search input and clicking "开始研究" starts a research task.
4. Stepper progresses through the 4 phases with correct dot states and colors.
5. Progress bar advances from 5% to 98%.
6. Research plan appears with correct sub-questions.
7. Report area shows streaming Markdown content in real time.
8. On completion, final report renders with proper Markdown formatting.
9. Sources appear with score badges and metadata.
10. Clicking "停止" cancels the running research, showing the warning alert.
11. Timer shows elapsed seconds while research is running.
12. Phase timing stats appear on completion.

- [ ] **Step 4: Commit any fixes**

```bash
cd frontend-vue && git add -A && git commit -m "fix: integration fixes from manual testing"
```

---

### Task 13: Final Polish

**Files:**
- Modify: `frontend-vue/src/styles/main.css`

- [ ] **Step 1: Add any remaining visual polish identified during integration testing**

Typical adjustments:
- Adjust stepper card background gradient for better contrast
- Tune spacing between components in ResearchPage grid
- Ensure sidebar collapse animation is smooth
- Verify scrollbar styling works in Chrome, Firefox, Safari

- [ ] **Step 2: Final commit**

```bash
cd frontend-vue && git add -A && git commit -m "style: final visual polish and spacing adjustments"
```
