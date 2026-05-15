import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchDocuments, uploadDocument, deleteDocument } from '@/api/documents'
import type { DocFile } from '@/api/documents'

export type { DocFile }

export const useDocumentsStore = defineStore('documents', () => {
  const files = ref<DocFile[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const totalChunks = computed(() => files.value.reduce((sum, f) => sum + f.chunks, 0))
  const totalSize = computed(() => files.value.reduce((sum, f) => sum + f.size, 0))

  async function loadFiles(): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      files.value = await fetchDocuments()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载文件列表失败'
    } finally {
      isLoading.value = false
    }
  }

  async function upload(file: File): Promise<void> {
    error.value = null
    try {
      await uploadDocument(file)
      await loadFiles()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '上传失败'
      throw e
    }
  }

  async function remove(fileId: string): Promise<void> {
    error.value = null
    try {
      await deleteDocument(fileId)
      await loadFiles()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '删除失败'
      throw e
    }
  }

  return { files, isLoading, error, totalChunks, totalSize, loadFiles, upload, remove }
})
