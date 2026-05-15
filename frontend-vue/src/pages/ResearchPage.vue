<template>
  <div>
    <div class="text-center mb-6">
      <h1 class="text-2xl font-bold bg-gradient-to-r from-brand-700 via-purple-500 to-pink-500 bg-clip-text text-transparent">
        🔬 Deep Research Agent
      </h1>
      <p class="text-sm text-gray-400 mt-1">
        Agentic RAG — 自主拆解问题 · 自适应检索 · 质量评估 · 报告合成
      </p>
    </div>

    <SearchForm
      :is-running="store.isRunning"
      @submit="onSubmit"
      @stop="onStop"
    />

    <div v-if="showContent" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-1">
        <AgentStepper />
        <ProgressPanel />
        <EventTimeline />
      </div>

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

    <n-alert
      v-if="store.isCancelled"
      type="warning"
      :bordered="false"
      class="mt-3"
      title="研究已被取消"
    >
      已保留部分结果。
    </n-alert>

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
