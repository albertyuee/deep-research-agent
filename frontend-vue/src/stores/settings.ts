import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchSettings, updateSettings, fetchSystemInfo } from '@/api/settings'
import type { SettingsData, SystemInfo } from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<SettingsData | null>(null)
  const systemInfo = ref<SystemInfo | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const successMsg = ref<string | null>(null)

  const hasSettings = computed(() => settings.value !== null)

  async function loadSettings(): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      const [s, info] = await Promise.all([fetchSettings(), fetchSystemInfo()])
      settings.value = s
      systemInfo.value = info
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载配置失败'
    } finally {
      isLoading.value = false
    }
  }

  async function saveSettings(patch: Parameters<typeof updateSettings>[0]): Promise<void> {
    isSaving.value = true
    error.value = null
    successMsg.value = null
    try {
      const result = await updateSettings(patch)
      await loadSettings()
      successMsg.value = result.need_restart
        ? '配置已保存，部分修改需重启后生效'
        : '配置已保存并生效'
      setTimeout(() => { successMsg.value = null }, 5000)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '保存失败'
    } finally {
      isSaving.value = false
    }
  }

  return { settings, systemInfo, isLoading, isSaving, error, successMsg, hasSettings, loadSettings, saveSettings }
})
