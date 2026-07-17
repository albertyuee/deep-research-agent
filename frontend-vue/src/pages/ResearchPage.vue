<template>
  <div>
    <div class="page-heading mb-5">
      <h1 class="text-xl font-bold text-gray-800">
        🔬 深度研究
      </h1>
      <p class="text-sm text-gray-400">
        从问题拆解到证据报告，全程展示研究路径
      </p>
    </div>

    <SearchForm
      :is-running="store.isRunning"
      @submit="onSubmit"
      @stop="onStop"
    />

    <div v-if="showContent" class="research-layout grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-1 research-sidebar">
        <AgentStepper />
        <ProgressPanel />
        <WebSearchCard />
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

    <div v-else class="welcome-empty">
      <div class="welcome-icon-wrap">
        <span class="welcome-icon-large">🔬</span>
      </div>
      <h2 class="welcome-title-text">开始你的深度研究</h2>
      <p class="welcome-desc">
        提出一个复杂问题，Agent 会规划路径、检索证据并生成带来源的结构化报告。
      </p>
      <div class="welcome-steps">
        <div v-for="(step, i) in steps" :key="i" class="welcome-step-item">
          <div class="welcome-step-num">{{ i + 1 }}</div>
          <div class="welcome-step-content">
            <div class="welcome-step-title">{{ step.title }}</div>
            <div class="welcome-step-desc">{{ step.desc }}</div>
          </div>
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
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useResearchStore } from '@/stores/research'
import { useResearch } from '@/composables/useResearch'
import SearchForm from '@/components/research/SearchForm.vue'
import AgentStepper from '@/components/research/AgentStepper.vue'
import ProgressPanel from '@/components/research/ProgressPanel.vue'
import EventTimeline from '@/components/research/EventTimeline.vue'
import WebSearchCard from '@/components/research/WebSearchCard.vue'
import ReportView from '@/components/report/ReportView.vue'
import SourceList from '@/components/report/SourceList.vue'
import type { ResearchMode } from '@/api/research'

const store = useResearchStore()
const { start, stop, resume, cleanup } = useResearch()

const showContent = computed(() => {
  return Boolean(
    store.isRunning
    || store.isCancelled
    || store.error
    || store.taskId
    || store.report
    || store.streamingReport
    || store.researchPlan.length
    || store.eventLog.length,
  )
})

const steps = [
  { title: '输入问题', desc: '输入你想深入研究的任何问题' },
  { title: 'Agent 自主研究', desc: '自动拆解 → 检索 → 评估 → 合成' },
  { title: '获取报告', desc: '结构化研究报告 + 可追溯引用来源' },
]

async function onSubmit(
  query: string,
  enableWebSearch: boolean,
  researchMode: ResearchMode,
  maxHops: number,
) {
  await start(query, enableWebSearch, researchMode, maxHops)
}

async function onStop() {
  await stop()
}

onBeforeUnmount(() => {
  cleanup()
})

onMounted(() => {
  void resume()
})
</script>

<style scoped>
.report-panel {
  min-height: 400px;
  background: #fff;
  border-radius: 14px;
  border: 1px solid #f3f4f6;
}

.research-sidebar {
  align-self: start;
}

@media (min-width: 1024px) {
  .research-sidebar {
    position: sticky;
    top: 20px;
    max-height: calc(100vh - 40px);
    overflow-y: auto;
    padding-right: 3px;
  }
}

/* Welcome / Empty State */
.welcome-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px 20px 20px;
  text-align: center;
}

.welcome-icon-wrap {
  margin-bottom: 14px;
}

.welcome-icon-large {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  font-size: 2rem;
  background: linear-gradient(135deg, #faf5ff 0%, #ede9fe 100%);
  border-radius: 20px;
  box-shadow: 0 8px 24px rgba(124, 58, 237, 0.12);
}

.welcome-title-text {
  font-size: 1.35rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.welcome-desc {
  font-size: 0.9rem;
  color: #9ca3af;
  max-width: 420px;
  line-height: 1.6;
  margin: 0 0 22px 0;
}

.welcome-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
  max-width: 820px;
}

.welcome-step-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: #fafbfc;
  border: 1px solid #f3f4f6;
  border-radius: 14px;
  padding: 14px;
  text-align: left;
  transition: all 0.2s ease;
}

.welcome-step-item:hover {
  border-color: #e9d5ff;
  background: #fafbff;
  box-shadow: 0 2px 12px rgba(124, 58, 237, 0.06);
}

.welcome-step-num {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #7c3aed, #a78bfa);
  color: #fff;
  font-weight: 700;
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.welcome-step-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #374151;
}

.welcome-step-desc {
  font-size: 0.78rem;
  color: #9ca3af;
  margin-top: 2px;
}

@media (max-width: 760px) {
  .page-heading {
    margin-bottom: 14px;
  }

  .welcome-empty {
    padding: 20px 4px 8px;
  }

  .welcome-steps {
    grid-template-columns: 1fr;
    max-width: 480px;
  }
}
</style>
