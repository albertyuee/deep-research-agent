<template>
  <div class="flex mb-4" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
    <div
      class="max-w-[80%] rounded-2xl px-4 py-3"
      :class="msg.role === 'user'
        ? 'bg-gradient-to-r from-brand-700 to-purple-500 text-white'
        : 'bg-gray-100 text-gray-800'"
    >
      <!-- User message: plain text -->
      <p v-if="msg.role === 'user'" class="text-sm whitespace-pre-wrap">{{ msg.content }}</p>

      <!-- Assistant message: markdown summary + sources + meta -->
      <div v-else>
        <div class="markdown-body text-sm" v-html="renderedContent" />
        <div class="flex items-center gap-2 mt-2 text-xs text-gray-400">
          <span v-if="msg.elapsedMs">{{ (msg.elapsedMs / 1000).toFixed(1) }}s</span>
        </div>

        <!-- Sources -->
        <div v-if="msg.sources && msg.sources.length" class="mt-2">
          <n-collapse>
            <n-collapse-item title="查看来源" name="sources">
              <div v-for="src in msg.sources" :key="src.chunk_id" class="source-card mb-2">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold text-gray-700">
                    {{ src.metadata?.doc_title || src.metadata?.source || src.chunk_id }}
                  </span>
                  <ScoreBadge :score="src.score" />
                </div>
                <p class="text-xs text-gray-500 line-clamp-3">{{ src.content?.slice(0, 300) }}</p>
              </div>
            </n-collapse-item>
          </n-collapse>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import ScoreBadge from '@/components/common/ScoreBadge.vue'
import type { ChatMessage } from '@/stores/chat'

const props = defineProps<{
  msg: ChatMessage
}>()

const renderedContent = computed(() => {
  return marked.parse(props.msg.content) as string
})
</script>
