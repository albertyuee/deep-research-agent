<template>
  <SettingsSection title="系统信息">
    <n-spin :show="loading">
      <div v-if="info" class="grid grid-cols-2 gap-4 text-sm">
        <div class="flex justify-between">
          <span class="text-gray-500">向量存储</span>
          <span class="font-semibold">{{ backendLabel }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-500">已索引文档</span>
          <span class="font-semibold">{{ info.chunk_count }} chunks</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-500">版本</span>
          <span class="font-semibold">{{ info.version }}</span>
        </div>
      </div>
    </n-spin>
  </SettingsSection>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SettingsSection from './SettingsSection.vue'
import type { SystemInfo } from '@/api/settings'

const props = defineProps<{ info: SystemInfo | null; loading: boolean }>()

const backendLabel = computed(() => {
  if (!props.info) return ''
  return props.info.vector_backend === 'milvus' ? 'Zilliz Cloud / Milvus' : 'ChromaDB (本地)'
})
</script>
