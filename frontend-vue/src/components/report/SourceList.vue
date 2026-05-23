<template>
  <div v-if="sources.length" class="mt-4">
    <n-divider />
    <h3 class="text-base font-semibold text-gray-700 mb-3">引用来源 ({{ uniqueSources.length }})</h3>

    <!-- Web sources -->
    <div v-if="webSources.length" class="mb-3">
      <h4 class="text-sm font-medium text-blue-600 mb-2">网络来源</h4>
      <div v-for="src in webSources" :key="src.chunk_id" class="source-card web-source">
        <div class="flex items-center gap-2 justify-between flex-wrap">
          <a
            v-if="src.metadata?.url"
            :href="src.metadata.url"
            target="_blank"
            rel="noopener noreferrer"
            class="font-semibold text-sm text-blue-700 hover:underline"
          >
            {{ src.metadata?.title || src.metadata?.url }}
            <span class="text-xs text-blue-400 ml-1">↗</span>
          </a>
          <span v-else class="font-semibold text-sm text-gray-800">
            {{ src.metadata?.title || src.metadata?.source || src.chunk_id }}
          </span>
          <ScoreBadge :score="src.score" />
        </div>
        <p class="text-xs text-gray-400 mt-1 truncate">
          {{ src.metadata?.url || '' }}
        </p>
        <p class="text-xs text-gray-500 mt-1.5 line-clamp-2">
          {{ src.content?.slice(0, 200) }}{{ src.content?.length > 200 ? '...' : '' }}
        </p>
      </div>
    </div>

    <!-- Local sources -->
    <div v-if="localSources.length">
      <h4 v-if="webSources.length" class="text-sm font-medium text-purple-600 mb-2">本地资料库</h4>
      <div v-for="src in localSources" :key="src.chunk_id" class="source-card local-source">
        <div class="flex items-center gap-2 justify-between flex-wrap">
          <span class="font-semibold text-sm text-gray-800">
            {{ src.metadata?.file_name || src.metadata?.source_path || src.metadata?.source || src.chunk_id }}
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

const webSources = computed(() =>
  uniqueSources.value.filter(s => s.metadata?.source_type === 'web')
)

const localSources = computed(() =>
  uniqueSources.value.filter(s => s.metadata?.source !== 'web')
)
</script>

<style scoped>
.source-card {
  background: #fafbfc;
  border: 1px solid #f3f4f6;
  border-radius: 10px;
  padding: 10px 14px;
  margin-bottom: 8px;
}
.web-source {
  border-left: 3px solid #93c5fd;
}
.local-source {
  border-left: 3px solid #c4b5fd;
}
.source-card a:hover {
  text-decoration: underline;
}
</style>
