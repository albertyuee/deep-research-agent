import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  const llmProvider = ref('siliconflow')
  const apiKey = ref('')
  const model = ref('')

  return { llmProvider, apiKey, model }
})
