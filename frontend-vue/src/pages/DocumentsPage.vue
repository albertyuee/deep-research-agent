<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">📁 资料管理</h1>
        <p class="text-sm text-gray-400">
          {{ store.files.length > 0 ? `${store.files.length} 个文件 · ${store.totalChunks} chunks · ${formatSize(store.totalSize)}` : '上传文档以扩展知识库' }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <n-input v-model:value="searchQuery" clearable placeholder="搜索文档名称或 ID" style="width: 220px">
          <template #prefix><n-icon><search-outline /></n-icon></template>
        </n-input>
        <n-button v-if="canUpload" type="primary" @click="showUpload = true">
          <template #icon><n-icon><cloud-upload-outline /></n-icon></template>
          上传文件
        </n-button>
      </div>
    </div>

    <n-alert v-if="store.error" type="error" :bordered="false" class="mb-4">
      {{ store.error }}
    </n-alert>

    <n-spin :show="store.isLoading">
      <div v-if="filteredFiles.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <DocumentCard
          v-for="f in filteredFiles"
          :key="f.id"
          :file="f"
          @preview="onPreview"
          @delete="onDelete"
        />
      </div>

      <div v-else class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-5xl mb-4">📂</div>
        <h3 class="text-lg font-semibold text-gray-700 mb-2">{{ searchQuery ? '没有匹配的文档' : '暂无文档' }}</h3>
        <p class="text-sm text-gray-400 max-w-sm mb-4">
          {{ searchQuery ? '请尝试其他文件名或文档 ID。' : '上传 PDF、Word、Markdown 或 TXT 文档，自动分块索引入知识库，立即可被检索。' }}
        </p>
        <n-button v-if="canUpload && !searchQuery" type="primary" @click="showUpload = true">
          <template #icon><n-icon><cloud-upload-outline /></n-icon></template>
          上传第一个文档
        </n-button>
      </div>
    </n-spin>

    <UploadDialog v-model:show="showUpload" />
    <PreviewDialog v-model:show="showPreview" :file="previewFile" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NIcon } from 'naive-ui'
import { CloudUploadOutline, SearchOutline } from '@vicons/ionicons5'
import { useDocumentsStore } from '@/stores/documents'
import type { DocFile } from '@/stores/documents'
import DocumentCard from '@/components/documents/DocumentCard.vue'
import UploadDialog from '@/components/documents/UploadDialog.vue'
import PreviewDialog from '@/components/documents/PreviewDialog.vue'
import { useAuthStore } from '@/stores/auth'

const store = useDocumentsStore()
const auth = useAuthStore()
const canUpload = computed(() => auth.user?.permissions.includes('document:upload') ?? true)
const searchQuery = ref('')
const filteredFiles = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  if (!keyword) return store.files
  return store.files.filter(file => `${file.name} ${file.id}`.toLowerCase().includes(keyword))
})
const showUpload = ref(false)
const showPreview = ref(false)
const previewFile = ref<DocFile | null>(null)

onMounted(() => {
  store.loadFiles()
})

function onPreview(file: DocFile) {
  previewFile.value = file
  showPreview.value = true
}

async function onDelete(fileId: string) {
  try {
    await store.remove(fileId)
  } catch {
    // Error handled by store
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>
