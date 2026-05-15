<template>
  <n-card :bordered="false" size="small" class="doc-card">
    <div class="flex items-start justify-between mb-2">
      <div class="flex items-center gap-2">
        <span class="text-xl">{{ fileIcon }}</span>
        <span class="font-semibold text-sm text-gray-800 truncate max-w-[140px]" :title="file.name">
          {{ file.name }}
        </span>
      </div>
      <n-tag :type="statusType" size="tiny">{{ statusLabel }}</n-tag>
    </div>

    <div class="text-xs text-gray-400 space-y-1 mb-3">
      <div>{{ file.chunks }} chunks · {{ formatSize(file.size) }}</div>
      <div>{{ formatTime(file.uploaded_at) }}</div>
    </div>

    <div class="flex gap-2">
      <n-button text size="small" type="primary" @click="$emit('preview', file)">
        <template #icon><n-icon><eye-outline /></n-icon></template>
        预览
      </n-button>
      <n-popconfirm @positive-click="$emit('delete', file.id)">
        <template #trigger>
          <n-button text size="small" type="error">
            <template #icon><n-icon><trash-outline /></n-icon></template>
            删除
          </n-button>
        </template>
        确定删除「{{ file.name }}」？此操作不可撤销。
      </n-popconfirm>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { EyeOutline, TrashOutline } from '@vicons/ionicons5'
import type { DocFile } from '@/stores/documents'

const props = defineProps<{ file: DocFile }>()

defineEmits<{
  preview: [file: DocFile]
  delete: [fileId: string]
}>()

const extIconMap: Record<string, string> = {
  pdf: '📕', docx: '📘', md: '📝', txt: '📄',
}
const fileIcon = computed(() => {
  const ext = props.file.name.split('.').pop()?.toLowerCase() || ''
  return extIconMap[ext] || '📎'
})

const statusType = computed(() => {
  return props.file.status === 'ready' ? 'success' : props.file.status === 'error' ? 'error' : 'warning'
})
const statusLabel = computed(() => {
  return props.file.status === 'ready' ? '已就绪' : props.file.status === 'error' ? '失败' : '处理中'
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return `${Math.floor(diff / 86400000)} 天前`
}
</script>

<style scoped>
.doc-card {
  border-radius: 14px;
  border: 1px solid #f3f4f6;
  transition: all 0.2s;
}
.doc-card:hover {
  border-color: #c4b5fd;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.08);
}
</style>
