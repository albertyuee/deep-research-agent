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
            <td class="text-xs"><n-tag size="tiny" :bordered="true">{{ eventTypeLabel(r.eventType) }}</n-tag></td>
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

const eventTypeLabels: Record<string, string> = {
  research_plan_start: '开始拆解',
  research_plan_chunk: '生成研究步骤',
  research_layer_start: '开始依赖层',
  retrieval_start: '开始检索',
  retrieval_result: '检索结果',
  web_search_start: '开始联网搜索',
  web_search_result: '联网搜索结果',
  retrieval_combined: '检索汇总',
  critique_start: '开始质量评估',
  critique_result: '质量评估结果',
  retry_triggered: '触发重试',
  reasoning_query: '生成多跳查询',
  reasoning_context: '提取多跳上下文',
  synthesis_start: '开始生成报告',
  synthesis_chunk: '生成报告中',
  timing: '后端计时',
  done: '研究完成',
  error: '错误',
}

function eventTypeLabel(eventType: string): string {
  return eventTypeLabels[eventType] || eventType
}
</script>
