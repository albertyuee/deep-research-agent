<template>
  <SettingsSection title="系统信息">
    <n-spin :show="loading">
      <div v-if="info" class="grid grid-cols-2 gap-4 text-sm">
        <div class="flex justify-between"><span class="text-gray-500">ChromaDB Chunks</span><span class="font-semibold">{{ info.chroma_chunks }}</span></div>
        <div class="flex justify-between"><span class="text-gray-500">版本</span><span class="font-semibold">{{ info.version }}</span></div>
      </div>
    </n-spin>
  </SettingsSection>
</template>

<script setup lang="ts">
import SettingsSection from './SettingsSection.vue'
import type { SystemInfo } from '@/stores/settings'

defineProps<{ info: SystemInfo | null; loading: boolean }>()
</script>
