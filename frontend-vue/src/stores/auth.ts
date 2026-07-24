import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchCurrentUser, login as loginApi, logout as logoutApi } from '@/api/auth'
import type { AuthUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const isLoading = ref(false)
  const authRequired = ref(false)
  const isAuthenticated = computed(() => Boolean(user.value))

  async function hydrate(): Promise<void> {
    isLoading.value = true
    try {
      user.value = await fetchCurrentUser()
      authRequired.value = false
    } catch (error) {
      user.value = null
      // Fail closed: a missing/failed auth endpoint must never be treated as
      // anonymous access, otherwise a stale backend can expose the research UI.
      authRequired.value = true
    } finally {
      isLoading.value = false
    }
  }

  async function login(email: string, password: string): Promise<void> {
    user.value = await loginApi(email, password)
    authRequired.value = false
  }

  function logout(): void {
    logoutApi()
    user.value = null
    authRequired.value = true
  }

  return { user, isLoading, authRequired, isAuthenticated, hydrate, login, logout }
})
