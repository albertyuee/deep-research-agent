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
