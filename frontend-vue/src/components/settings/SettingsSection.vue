<template>
  <n-card :bordered="false" size="small" class="mb-4 settings-card">
    <template #header>
      <span class="font-semibold text-gray-700">{{ title }}</span>
    </template>
    <template #header-extra>
      <slot name="actions" />
    </template>
    <slot />
  </n-card>
</template>

<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<style scoped>
.settings-card { border-radius: 14px; border: 1px solid #f3f4f6; }
</style>
