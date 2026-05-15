<template>
  <n-modal v-model:show="visible" preset="card" title="文件预览" style="width:640px">
    <div v-if="file">
      <div class="text-sm text-gray-500 mb-3 space-y-1">
        <div><strong>文件名:</strong> {{ file.name }}</div>
        <div><strong>大小:</strong> {{ formatSize(file.size) }} · <strong>Chunks:</strong> {{ file.chunks }}</div>
        <div><strong>上传时间:</strong> {{ file.uploaded_at }}</div>
        <div><strong>状态:</strong> <n-tag :type="file.status === 'ready' ? 'success' : 'warning'" size="tiny">{{ file.status }}</n-tag></div>
      </div>
      <n-divider />
      <p class="text-xs text-gray-400">完整内容预览需要从向量库读取，此处展示文件元信息。</p>
    </div>
    <template #footer>
      <n-button @click="visible = false">关闭</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import type { DocFile } from '@/stores/documents'

const visible = defineModel<boolean>('show', { required: true })
defineProps<{ file: DocFile | null }>()

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>
