<template>
  <n-card
    v-if="store.webSearchResults.length > 0"
    title="🌐 网络搜索结果"
    size="small"
    :bordered="false"
    class="mb-3"
  >
    <template #header-extra>
      <n-tag size="small" type="info">{{ store.webSearchResults.length }} 个网页</n-tag>
    </template>

    <div class="max-h-80 overflow-y-auto">
      <div
        v-for="(item, i) in store.webSearchResults"
        :key="i"
        class="web-result-item"
      >
        <div class="flex items-start gap-2">
          <span class="text-xs text-gray-300 font-mono flex-shrink-0 pt-0.5">
            {{ i + 1 }}.
          </span>
          <div class="min-w-0">
            <a
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline truncate block"
            >
              {{ item.title || '无标题' }}
            </a>
            <p class="text-xs text-gray-500 mt-0.5 line-clamp-2">
              {{ item.content }}
            </p>
            <div class="flex items-center gap-2 mt-1">
              <span class="text-xs text-gray-300 truncate max-w-[200px]">
                {{ item.url }}
              </span>
              <ScoreBadge v-if="item.score" :score="item.score" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { useResearchStore } from '@/stores/research'
import ScoreBadge from '@/components/common/ScoreBadge.vue'

const store = useResearchStore()
</script>

<style scoped>
.web-result-item {
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
}
.web-result-item:last-child {
  border-bottom: none;
}
</style>
