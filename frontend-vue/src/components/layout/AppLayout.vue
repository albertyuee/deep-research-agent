<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-layout has-sider position="absolute" style="height: 100vh;">
      <SideNav />
      <n-layout-content>
        <div class="p-6 max-w-[1400px] mx-auto">
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
