<template>
  <n-modal v-model:show="visible" preset="card" title="上传文档" style="width:480px">
    <n-upload
      multiple
      :max="5"
      accept=".pdf,.docx,.md,.txt"
      :custom-request="handleUpload"
      :show-file-list="true"
    >
      <n-upload-dragger>
        <div class="text-center py-8">
          <div class="text-3xl mb-2">📁</div>
          <p class="text-sm text-gray-600">点击或拖拽文件到此处上传</p>
          <p class="text-xs text-gray-400 mt-1">支持 PDF、Word、Markdown、TXT</p>
        </div>
      </n-upload-dragger>
    </n-upload>
    <div v-if="uploadError" class="mt-3">
      <n-alert type="error" :bordered="false">{{ uploadError }}</n-alert>
    </div>
    <template #footer>
      <n-button @click="visible = false">关闭</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useDocumentsStore } from '@/stores/documents'

const visible = defineModel<boolean>('show', { required: true })
const store = useDocumentsStore()
const uploadError = ref<string | null>(null)

async function handleUpload(options: { file: File; onFinish: () => void; onError: () => void }) {
  uploadError.value = null
  try {
    await store.upload(options.file)
    options.onFinish()
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败'
    options.onError()
  }
}
</script>
