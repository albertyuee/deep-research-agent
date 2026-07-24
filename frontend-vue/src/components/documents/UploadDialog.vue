<template>
  <n-modal v-model:show="visible" preset="card" title="上传文档" style="width:520px">
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
    <n-form label-placement="left" label-width="90" class="mt-4">
      <n-form-item label="访问范围">
        <n-select v-model:value="visibility" :options="visibilityOptions" />
      </n-form-item>
      <n-form-item v-if="visibility === 'departments'" label="可见部门">
        <n-select v-model:value="selectedDepartmentIds" multiple :options="departmentOptions" placeholder="选择一个或多个部门" />
      </n-form-item>
    </n-form>
    <n-alert v-if="uploadSuccess" type="success" :bordered="false" class="mt-3">
      上传成功：{{ uploadSuccess.name }}，已生成 {{ uploadSuccess.chunks }} 个文档块。<br />
      访问范围：{{ uploadSuccess.visibility }}
    </n-alert>
    <div v-if="uploadError" class="mt-3">
      <n-alert type="error" :bordered="false">{{ uploadError }}</n-alert>
    </div>
    <template #footer>
      <n-button @click="visible = false">关闭</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useDocumentsStore } from '@/stores/documents'
import { useAuthStore } from '@/stores/auth'
import { fetchDepartments } from '@/api/auth'
import type { Department } from '@/api/auth'

const visible = defineModel<boolean>('show', { required: true })
const store = useDocumentsStore()
const auth = useAuthStore()
const uploadError = ref<string | null>(null)
const uploadSuccess = ref<{ name: string; chunks: number; visibility: string } | null>(null)
const visibility = ref('private')
const selectedDepartmentIds = ref<string[]>([])
const departments = ref<Department[]>([])
const visibilityOptions = computed(() => [
  { label: '仅自己可见', value: 'private' },
  { label: '本部门可见', value: 'department' },
  ...(auth.user?.role === 'admin' ? [{ label: '指定部门可见', value: 'departments' }] : []),
  { label: '全部人员可见', value: 'workspace' },
  { label: '公开', value: 'public' },
])
const departmentOptions = computed(() => departments.value.map(item => ({ label: item.name, value: item.id })))

watch(visible, async (shown) => {
  if (!shown) {
    uploadError.value = null
    uploadSuccess.value = null
    return
  }
  if (auth.user?.role === 'admin' && !departments.value.length) {
    try { departments.value = await fetchDepartments() } catch { /* 上传时后端仍会校验权限 */ }
  }
})

watch(visibility, (value) => {
  if (value !== 'departments') selectedDepartmentIds.value = []
})

async function handleUpload(options: { file: { file?: File; name: string }; onFinish: () => void; onError: () => void }) {
  uploadError.value = null
  uploadSuccess.value = null
  const realFile = options.file.file
  if (!realFile) {
    uploadError.value = '无法读取文件'
    options.onError()
    return
  }
  try {
    const result = await store.upload(realFile, {
      visibility: visibility.value,
      departmentIds: selectedDepartmentIds.value,
    })
    uploadSuccess.value = {
      name: result.name,
      chunks: result.chunks,
      visibility: visibilityOptions.value.find(item => item.value === visibility.value)?.label || visibility.value,
    }
    options.onFinish()
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败'
    options.onError()
  }
}
</script>
