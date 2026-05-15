<template>
  <div v-if="sources.length" class="mt-4">
    <n-divider />
    <h3 class="text-base font-semibold text-gray-700 mb-3">\u{1F4CE} 引用来源 ({{ uniqueSources.length }})</h3>
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
