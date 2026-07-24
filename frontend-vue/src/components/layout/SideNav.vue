<template>
  <n-layout-sider
    bordered
    collapse-mode="width"
    :collapsed-width="64"
    :width="200"
    :collapsed="collapsed"
    show-trigger
    @collapse="collapsed = true"
    @expand="collapsed = false"
  >
    <div class="flex flex-col h-full">
      <div class="p-4 flex items-center gap-2" :class="collapsed ? 'justify-center' : ''">
        <span class="text-2xl">🔬</span>
        <span v-if="!collapsed" class="font-bold text-base text-gray-800 whitespace-nowrap">
          Deep Research
        </span>
      </div>

      <n-menu
        :value="currentRoute"
        :collapsed="collapsed"
        :collapsed-width="64"
        :options="menuOptions"
        @update:value="navigate"
      />

      <div class="mt-auto p-3">
        <div v-if="auth.user" class="account-panel" :class="{ 'account-panel--collapsed': collapsed }">
          <div class="account-avatar">{{ userInitials }}</div>
          <div v-if="!collapsed" class="account-details">
            <div class="account-name" :title="auth.user.display_name">{{ auth.user.display_name }}</div>
            <span class="account-role">{{ roleLabel }}</span>
          </div>
          <n-tooltip v-if="collapsed" placement="right">
            <template #trigger><span class="account-collapsed-name">{{ auth.user.display_name }}</span></template>
            {{ auth.user.display_name }} · {{ roleLabel }}
          </n-tooltip>
          <n-button v-if="!collapsed" class="account-logout" text @click="logout">
            <template #icon><n-icon><log-out-outline /></n-icon></template>
            退出登录
          </n-button>
        </div>
        <n-button
          v-if="!collapsed"
          text
          size="small"
          @click="collapsed = !collapsed"
          class="text-gray-400"
        >
          <template #icon><n-icon><chevron-back /></n-icon></template>
          收起菜单
        </n-button>
      </div>
    </div>
  </n-layout-sider>
</template>

<script setup lang="ts">
import { ref, computed, h, onBeforeUnmount, onMounted, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  SearchOutline, FlashOutline, DocumentTextOutline,
  SettingsOutline, ChevronBack, ShieldCheckmarkOutline, LogOutOutline
} from '@vicons/ionicons5'
import { useAuthStore } from '@/stores/auth'
import { useResearchStore } from '@/stores/research'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const auth = useAuthStore()
const roleLabel = computed(() => ({ admin: '管理员', researcher: '研究者', guest: '访客' }[auth.user?.role || 'guest']))
const userInitials = computed(() => {
  const name = auth.user?.display_name?.trim() || 'U'
  return Array.from(name).slice(0, 2).join('').toUpperCase()
})

const currentRoute = computed(() => route.path)

let compactQuery: MediaQueryList | null = null

function syncCompactNavigation(event: MediaQueryListEvent | MediaQueryList) {
  if (event.matches) collapsed.value = true
}

onMounted(() => {
  compactQuery = window.matchMedia('(max-width: 900px)')
  syncCompactNavigation(compactQuery)
  compactQuery.addEventListener('change', syncCompactNavigation)
})

onBeforeUnmount(() => {
  compactQuery?.removeEventListener('change', syncCompactNavigation)
})

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = computed(() => {
  const permissions = auth.user?.permissions || []
  return [
    { label: '深度研究', key: '/', icon: renderIcon(SearchOutline), allowed: permissions.includes('research:create') },
    { label: '快速检索', key: '/quick-search', icon: renderIcon(FlashOutline), allowed: permissions.includes('research:create') },
    { label: '资料管理', key: '/documents', icon: renderIcon(DocumentTextOutline), allowed: permissions.includes('document:read') },
    { label: '系统设置', key: '/settings', icon: renderIcon(SettingsOutline), allowed: permissions.includes('settings:read') },
    { label: '管理后台', key: '/admin', icon: renderIcon(ShieldCheckmarkOutline), allowed: permissions.includes('user:manage') },
  ].filter(item => item.allowed).map(({ allowed: _allowed, ...item }) => item)
})

function navigate(key: string) {
  router.push(key)
}

function logout() {
  const research = useResearchStore()
  research.reset()
  auth.logout()
  router.replace('/login')
}
</script>

<style scoped>
.account-panel {
  min-height: 58px;
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  padding: 9px 8px;
  margin-bottom: 12px;
  border: 1px solid #ede9fe;
  border-radius: 12px;
  background: linear-gradient(135deg, #faf5ff 0%, #f5f3ff 100%);
}

.account-panel--collapsed {
  display: flex;
  justify-content: center;
  padding: 8px 4px;
}

.account-avatar {
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: #fff;
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.account-details {
  min-width: 0;
  flex: 1;
}

.account-name {
  overflow: hidden;
  color: #312e81;
  font-size: 12px;
  font-weight: 650;
  line-height: 17px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-role {
  display: inline-flex;
  margin-top: 2px;
  padding: 1px 6px;
  border-radius: 999px;
  color: #6d28d9;
  background: rgba(124, 58, 237, 0.1);
  font-size: 10px;
  line-height: 15px;
}

.account-logout {
  grid-column: 1 / -1;
  width: 100%;
  height: 28px;
  justify-content: center;
  color: #8b5cf6;
  font-size: 12px;
}

.account-logout:hover {
  color: #6d28d9;
  background: rgba(124, 58, 237, 0.08);
}

.account-collapsed-name {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
}
</style>
