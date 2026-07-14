<template>
  <div class="flex flex-col gap-3">
    <n-card v-if="store.researchPlan.length" title="研究路径" size="small" :bordered="false" class="plan-card">
      <template #header-extra>
        <div class="flex items-center gap-2">
          <n-tag size="small" :type="store.researchMode === 'multihop' ? 'warning' : 'info'">
            {{ modeLabel(store.researchMode) }}
          </n-tag>
          <n-tag size="small" type="info">{{ store.researchPlan.length }} 个子问题</n-tag>
        </div>
      </template>
      <div class="plan-list" :class="{ linked: isLinkedPlan }">
        <div v-for="(plan, index) in store.researchPlan" :key="plan.index" class="plan-node-wrap">
          <article class="plan-node" :class="`state-${planStatus(plan)}`">
            <div class="plan-node-header">
              <span class="plan-index">{{ plan.index }}</span>
              <div class="plan-title-wrap">
                <div class="plan-title">{{ plan.question }}</div>
                <div class="plan-meta">
                  <span>{{ strategyIcon(plan.strategy) }} {{ strategyLabel(plan.strategy) }}</span>
                  <span>Hop {{ plan.hop || 1 }}</span>
                  <span v-if="plan.dependsOn?.length">依赖 {{ plan.dependsOn.join('、') }}</span>
                </div>
              </div>
              <n-tag size="tiny" :type="planStatusType(planStatus(plan))">
                {{ planStatusLabel(planStatus(plan)) }}
              </n-tag>
            </div>
            <div v-if="plan.rationale" class="plan-rationale">{{ plan.rationale }}</div>
          </article>
          <div v-if="isLinkedPlan && index < store.researchPlan.length - 1" class="dependency-connector">
            <span>↓</span>
            <span>传递实体与事实</span>
          </div>
        </div>
      </div>
    </n-card>

    <n-card v-if="store.reasoningContexts.length" title="多跳上下文" size="small" :bordered="false">
      <div v-for="context in store.reasoningContexts" :key="context.step" class="mb-3 last:mb-0">
        <div class="flex items-center gap-2 mb-1">
          <n-tag size="small" :type="context.lowConfidence ? 'warning' : 'info'">Hop {{ context.hop }}</n-tag>
          <span class="text-sm text-gray-600">步骤 {{ context.step }}</span>
          <span class="text-xs text-gray-400">
            {{ context.entityCount }} 个实体 / {{ context.factCount }} 条事实
          </span>
        </div>
        <div class="text-xs text-gray-500 p-2 bg-gray-50 rounded-lg">
          {{ context.summary }}
        </div>
      </div>
    </n-card>

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

    <n-card v-if="store.critiqueResults.length" title="质量评估" size="small" :bordered="false">
      <div v-for="c in store.critiqueResults" :key="c.step" class="mb-3 last:mb-0">
        <div class="flex items-center gap-2 mb-1">
          <n-tag :type="c.passed ? 'success' : 'warning'" size="small">
            {{ c.passed ? '\u2713 PASS' : '\u26A0 FAIL' }}
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
            \u{1F4A1} 建议: {{ c.retrySuggestion }}
          </div>
        </div>
      </div>
    </n-card>

    <n-card v-if="store.retryHistory.length" title="重试历史" size="small" :bordered="false">
      <div v-for="h in store.retryHistory" :key="h.attempt" class="text-sm mb-1">
        <strong>第 {{ h.attempt }} 次:</strong>
        上次评分 <ScoreBadge :score="h.score" />
        <span v-if="h.suggestion" class="text-xs text-gray-400"> — {{ h.suggestion }}</span>
      </div>
    </n-card>

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
import { useResearchStore, type PlanItem } from '@/stores/research'
import ScoreBadge from '@/components/common/ScoreBadge.vue'

const store = useResearchStore()

type PlanStatus = 'waiting' | 'running' | 'retrieved' | 'complete' | 'error'

const isLinkedPlan = computed(() => (
  store.researchMode === 'multihop'
  || store.researchPlan.some(plan => Boolean(plan.dependsOn?.length))
))

const totalTime = computed(() => {
  return Object.values(store.phaseDurations).reduce((a, b) => a + b, 0)
})

const strategyIconMap: Record<string, string> = {
  semantic: '\u{1F9E0}',
  keyword: '\u{1F511}',
  hybrid: '\u{1F500}',
}

function strategyIcon(strategy: string): string {
  return strategyIconMap[strategy] || '\u2753'
}

function strategyLabel(strategy: string): string {
  return ({ semantic: '语义检索', keyword: '关键词检索', hybrid: '混合检索' } as Record<string, string>)[strategy] || strategy
}

function planStatus(plan: PlanItem): PlanStatus {
  if (store.report || store.phaseStates.synthesis === 'complete') return 'complete'

  const critiqueItems = store.critiqueResults.filter(item => item.step === plan.index)
  const latestCritique = critiqueItems[critiqueItems.length - 1]
  if (latestCritique?.passed) return 'complete'

  const isCurrent = store.retrievalProgress?.step === plan.index
  if (isCurrent && (store.phaseStates.retrieval === 'running' || store.phaseStates.critique === 'running')) {
    return 'running'
  }

  const retrievalFinished = store.eventLog.some(event => (
    event.eventType === 'retrieval_result' && Number(event.data.step) === plan.index
  ))
  if (retrievalFinished) return 'retrieved'

  if (isCurrent && store.error) return 'error'
  return 'waiting'
}

function planStatusLabel(status: PlanStatus): string {
  return ({
    waiting: '等待',
    running: '执行中',
    retrieved: '已检索',
    complete: '完成',
    error: '异常',
  } as Record<PlanStatus, string>)[status]
}

function planStatusType(status: PlanStatus): 'default' | 'info' | 'success' | 'warning' | 'error' {
  return ({
    waiting: 'default',
    running: 'info',
    retrieved: 'warning',
    complete: 'success',
    error: 'error',
  } as Record<PlanStatus, 'default' | 'info' | 'success' | 'warning' | 'error'>)[status]
}

function modeLabel(mode: string): string {
  return ({ auto: '自动规划', parallel: '并列研究', multihop: '多跳推理' } as Record<string, string>)[mode] || mode
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

<style scoped>
.plan-card {
  border: 1px solid #f0edfa;
  border-radius: 14px;
}

.plan-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-node {
  padding: 10px;
  border: 1px solid #eceef2;
  border-radius: 11px;
  background: #fff;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.plan-node.state-running {
  border-color: #a78bfa;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.08);
}

.plan-node.state-complete {
  border-color: #bbf7d0;
  background: #fbfffc;
}

.plan-node.state-error {
  border-color: #fecaca;
  background: #fffafa;
}

.plan-node-header {
  display: flex;
  align-items: flex-start;
  gap: 9px;
}

.plan-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 25px;
  height: 25px;
  flex: 0 0 25px;
  border-radius: 8px;
  background: #ede9fe;
  color: #6d28d9;
  font-size: 0.72rem;
  font-weight: 800;
}

.plan-title-wrap {
  min-width: 0;
  flex: 1;
}

.plan-title {
  color: #374151;
  font-size: 0.78rem;
  font-weight: 650;
  line-height: 1.45;
}

.plan-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 9px;
  margin-top: 5px;
  color: #9ca3af;
  font-size: 0.65rem;
}

.plan-rationale {
  margin: 8px 0 0 34px;
  padding-top: 7px;
  border-top: 1px dashed #eceef2;
  color: #8b8f98;
  font-size: 0.68rem;
  line-height: 1.45;
}

.dependency-connector {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 22px;
  color: #8b5cf6;
  font-size: 0.62rem;
  font-weight: 600;
}

.plan-list.linked {
  gap: 0;
}
</style>
