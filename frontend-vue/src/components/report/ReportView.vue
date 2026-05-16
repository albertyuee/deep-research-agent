<template>
  <div class="report-container">
    <div v-if="!hasContent && !isStreaming" class="flex flex-col items-center justify-center py-20 text-gray-400">
      <span class="text-4xl mb-3">📊</span>
      <p class="text-sm">{{ isRunning ? 'Agent 正在准备报告...' : '输入研究问题开始深度研究' }}</p>
      <div v-if="isRunning" class="typing-cursor mt-1" />
    </div>
    <div v-else-if="isStreaming && !finalReport" class="report-content-wrapper relative">
      <div class="markdown-body" v-html="renderedStreaming" />
      <div class="typing-cursor" />
      <div class="text-xs text-gray-400 mt-2">正在生成中...</div>
    </div>
    <div v-else class="report-content-wrapper">
      <div class="markdown-body" v-html="renderedReport" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  report: string
  streamingReport: string
  isRunning: boolean
}>()

const hasContent = computed(() => props.report || props.streamingReport)
const isStreaming = computed(() => props.isRunning && props.streamingReport)
const finalReport = computed(() => props.report)

const renderedReport = computed(() => {
  if (!props.report) return ''
  return marked.parse(props.report) as string
})

const renderedStreaming = computed(() => {
  if (!props.streamingReport) return ''
  return marked.parse(props.streamingReport) as string
})
</script>

<style scoped>
.report-container { min-height: 300px; }
.report-content-wrapper :deep(.markdown-body) { font-size: 0.925rem; line-height: 1.75; color: #374151; }
.report-content-wrapper :deep(.markdown-body h1) { font-size: 1.5rem; font-weight: 700; color: #1f2937; margin: 1.5em 0 0.5em; }
.report-content-wrapper :deep(.markdown-body h2) { font-size: 1.25rem; font-weight: 600; color: #374151; margin: 1.25em 0 0.4em; border-bottom: 1px solid #f3f4f6; padding-bottom: 0.3em; }
.report-content-wrapper :deep(.markdown-body h3) { font-size: 1.1rem; font-weight: 600; color: #4b5563; margin: 1em 0 0.3em; }
.report-content-wrapper :deep(.markdown-body p) { margin: 0.6em 0; }
.report-content-wrapper :deep(.markdown-body ul), .report-content-wrapper :deep(.markdown-body ol) { padding-left: 1.5em; }
.report-content-wrapper :deep(.markdown-body li) { margin: 0.3em 0; }
.report-content-wrapper :deep(.markdown-body code) { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; }
.report-content-wrapper :deep(.markdown-body pre) { background: #1f2937; color: #e5e7eb; padding: 16px; border-radius: 10px; overflow-x: auto; }
.report-content-wrapper :deep(.markdown-body blockquote) { border-left: 3px solid #c4b5fd; padding-left: 14px; color: #6b7280; margin: 0.8em 0; }
.report-content-wrapper :deep(.markdown-body a) { color: #7c3aed; text-decoration: underline; }
</style>
