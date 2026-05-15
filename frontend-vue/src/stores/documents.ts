import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface DocFile {
  name: string
  size: number
  status: 'uploading' | 'processing' | 'ready' | 'error'
}

export const useDocumentsStore = defineStore('documents', () => {
  const files = ref<DocFile[]>([])

  return { files }
})
