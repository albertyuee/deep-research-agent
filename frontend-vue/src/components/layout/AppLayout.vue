<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-layout has-sider position="absolute" style="height: 100vh;">
      <SideNav />
      <n-layout-content>
        <div class="content-shell max-w-[1400px] mx-auto">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </div>
      </n-layout-content>
    </n-layout>
  </n-config-provider>
</template>

<script setup lang="ts">
import { zhCN, dateZhCN } from 'naive-ui'
import SideNav from './SideNav.vue'

const themeOverrides = {
  common: {
    primaryColor: '#7c3aed',
    primaryColorHover: '#9333ea',
    primaryColorPressed: '#6d28d9',
    primaryColorSuppl: '#a78bfa',
    borderRadius: '10px',
  },
}
</script>

<style scoped>
.content-shell {
  padding: 24px;
}

@media (max-width: 768px) {
  .content-shell {
    padding: 14px 12px 28px;
  }
}
</style>
