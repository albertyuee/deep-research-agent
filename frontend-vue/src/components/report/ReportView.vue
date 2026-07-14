<template>
  <div class="report-container">
    <div v-if="!hasContent" class="report-empty">
      <span class="text-4xl mb-3">📊</span>
      <p class="text-sm">{{ isRunning ? 'Agent 正在准备报告...' : '输入研究问题开始深度研究' }}</p>
      <div v-if="isRunning" class="typing-cursor mt-1" />
    </div>

    <div v-else class="report-content-wrapper">
      <div class="report-toolbar">
        <div>
          <div class="report-status-title">{{ isStreaming ? '正在生成研究报告' : '研究报告已生成' }}</div>
          <div class="report-status-meta">
            {{ documentStats.characters }} 字 · {{ documentStats.sections }} 个章节
          </div>
        </div>
        <div class="toolbar-actions">
          <n-button size="small" secondary :disabled="!activeMarkdown" @click="copyReport">
            <template #icon><n-icon><copy-outline /></n-icon></template>
            {{ copyState === 'copied' ? '已复制' : '复制' }}
          </n-button>
          <n-button size="small" secondary :disabled="!activeMarkdown" @click="downloadMarkdown">
            <template #icon><n-icon><download-outline /></n-icon></template>
            导出 Markdown
          </n-button>
        </div>
      </div>

      <nav v-if="!isStreaming && renderedDocument.toc.length > 1" class="report-toc" aria-label="报告目录">
        <div class="toc-title">报告目录</div>
        <div class="toc-links">
          <a
            v-for="item in renderedDocument.toc"
            :key="item.id"
            :href="`#${item.id}`"
            class="toc-link"
            :class="`level-${item.level}`"
          >
            {{ item.text }}
          </a>
        </div>
      </nav>

      <div class="markdown-body" v-html="renderedDocument.html" />
      <div v-if="isStreaming" class="streaming-indicator">
        <div class="typing-cursor" />
        <span>正在生成中...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { NIcon } from 'naive-ui'
import { CopyOutline, DownloadOutline } from '@vicons/ionicons5'

interface TocItem {
  id: string
  text: string
  level: number
}

const props = defineProps<{
  report: string
  streamingReport: string
  isRunning: boolean
}>()

const copyState = ref<'idle' | 'copied'>('idle')
const activeMarkdown = computed(() => props.report || props.streamingReport || '')
const hasContent = computed(() => Boolean(activeMarkdown.value))
const isStreaming = computed(() => props.isRunning && Boolean(props.streamingReport) && !props.report)

const renderedDocument = computed(() => {
  if (!activeMarkdown.value) return { html: '', toc: [] as TocItem[] }

  const rawHtml = marked.parse(activeMarkdown.value) as string
  const cleanHtml = DOMPurify.sanitize(rawHtml, { USE_PROFILES: { html: true } })
  const documentNode = new DOMParser().parseFromString(cleanHtml, 'text/html')
  const toc: TocItem[] = []

  documentNode.querySelectorAll('h1, h2, h3').forEach((heading, index) => {
    const text = heading.textContent?.trim() || `章节 ${index + 1}`
    const slug = text
      .toLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48)
    const id = `report-section-${index + 1}-${slug || 'section'}`
    const level = Number(heading.tagName.slice(1))
    heading.id = id
    toc.push({ id, text, level })
  })

  return { html: documentNode.body.innerHTML, toc }
})

const documentStats = computed(() => ({
  characters: activeMarkdown.value.replace(/\s/g, '').length,
  sections: renderedDocument.value.toc.length,
}))

async function copyReport() {
  if (!activeMarkdown.value) return
  await navigator.clipboard.writeText(activeMarkdown.value)
  copyState.value = 'copied'
  window.setTimeout(() => { copyState.value = 'idle' }, 1600)
}

function downloadMarkdown() {
  if (!activeMarkdown.value) return
  const blob = new Blob([activeMarkdown.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  const date = new Date().toISOString().slice(0, 10)
  anchor.href = url
  anchor.download = `deep-research-${date}.md`
  anchor.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.report-container {
  min-height: 300px;
}

.report-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #9ca3af;
}

.report-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #f0f1f4;
}

.report-status-title {
  color: #374151;
  font-size: 0.82rem;
  font-weight: 700;
}

.report-status-meta {
  margin-top: 2px;
  color: #9ca3af;
  font-size: 0.68rem;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.report-toc {
  margin-bottom: 20px;
  padding: 13px 15px;
  border: 1px solid #ede9fe;
  border-radius: 12px;
  background: #faf9ff;
}

.toc-title {
  margin-bottom: 8px;
  color: #4c1d95;
  font-size: 0.76rem;
  font-weight: 750;
}

.toc-links {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 5px 14px;
}

.toc-link {
  overflow: hidden;
  color: #6b7280;
  font-size: 0.7rem;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toc-link:hover {
  color: #7c3aed;
}

.toc-link.level-3 {
  padding-left: 12px;
  color: #9ca3af;
}

.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  color: #9ca3af;
  font-size: 0.72rem;
}

.report-content-wrapper :deep(.markdown-body) {
  color: #374151;
  font-size: 0.925rem;
  line-height: 1.78;
}

.report-content-wrapper :deep(.markdown-body h1) { scroll-margin-top: 24px; font-size: 1.5rem; font-weight: 700; color: #1f2937; margin: 1.5em 0 0.5em; }
.report-content-wrapper :deep(.markdown-body h2) { scroll-margin-top: 24px; font-size: 1.25rem; font-weight: 600; color: #374151; margin: 1.25em 0 0.4em; border-bottom: 1px solid #f3f4f6; padding-bottom: 0.3em; }
.report-content-wrapper :deep(.markdown-body h3) { scroll-margin-top: 24px; font-size: 1.1rem; font-weight: 600; color: #4b5563; margin: 1em 0 0.3em; }
.report-content-wrapper :deep(.markdown-body p) { margin: 0.6em 0; }
.report-content-wrapper :deep(.markdown-body ul), .report-content-wrapper :deep(.markdown-body ol) { padding-left: 1.5em; }
.report-content-wrapper :deep(.markdown-body li) { margin: 0.3em 0; }
.report-content-wrapper :deep(.markdown-body code) { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; }
.report-content-wrapper :deep(.markdown-body pre) { background: #1f2937; color: #e5e7eb; padding: 16px; border-radius: 10px; overflow-x: auto; }
.report-content-wrapper :deep(.markdown-body blockquote) { border-left: 3px solid #c4b5fd; padding-left: 14px; color: #6b7280; margin: 0.8em 0; }
.report-content-wrapper :deep(.markdown-body a) { color: #7c3aed; text-decoration: underline; }

@media (max-width: 640px) {
  .report-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-actions {
    width: 100%;
  }

  .toolbar-actions :deep(.n-button) {
    flex: 1;
  }

  .toc-links {
    grid-template-columns: 1fr;
  }
}
</style>
