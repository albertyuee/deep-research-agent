<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50 p-4">
    <n-card title="登录 Deep Research" class="w-full max-w-md" :bordered="false">
      <n-alert v-if="error" type="error" :bordered="false" class="mb-4">{{ error }}</n-alert>
      <n-form @submit.prevent="submit">
        <n-form-item label="邮箱">
          <n-input v-model:value="email" type="text" placeholder="name@example.com" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="password" type="password" show-password-on="click" placeholder="请输入密码" @keyup.enter="submit" />
        </n-form-item>
        <n-button type="primary" block :loading="loading" attr-type="submit">登录</n-button>
      </n-form>
      <p class="text-xs text-gray-400 mt-4">管理员首次登录前，请在 config/.env 配置 AUTH_ADMIN_EMAIL 和 AUTH_ADMIN_PASSWORD。</p>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useResearchStore } from '@/stores/research'

const router = useRouter()
const auth = useAuthStore()
const research = useResearchStore()
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  if (!email.value.trim() || !password.value) {
    error.value = '请输入邮箱和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    // A login may be a switch from a previous account. Never carry the
    // previous account's research report into the new session.
    research.reset()
    await auth.login(email.value, password.value)
    await router.replace('/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>
