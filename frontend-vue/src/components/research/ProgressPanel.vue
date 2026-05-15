<template>
  <div class="flex flex-col gap-3">
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
import { useResearchStore } from '@/stores/research'
import ScoreBadge from '@/components/common/ScoreBadge.vue'

const store = useResearchStore()

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
