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
  SettingsOutline, ChevronBack
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

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

const menuOptions = [
  { label: '深度研究', key: '/', icon: renderIcon(SearchOutline) },
  { label: '快速检索', key: '/quick-search', icon: renderIcon(FlashOutline) },
  { label: '资料管理', key: '/documents', icon: renderIcon(DocumentTextOutline) },
  { label: '系统设置', key: '/settings', icon: renderIcon(SettingsOutline) },
]

function navigate(key: string) {
  router.push(key)
}
</script>
