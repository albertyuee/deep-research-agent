<template>
  <div class="flex flex-wrap gap-2 mb-3">
    <n-tag
      v-for="(q, i) in suggestions"
      :key="i"
      :bordered="true"
      type="info"
      size="small"
      class="cursor-pointer"
      :disabled="disabled"
      @click="$emit('select', q)"
    >
      {{ q.slice(0, 40) }}{{ q.length > 40 ? '...' : '' }}
    </n-tag>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  disabled: boolean
}>()

defineEmits<{
  select: [query: string]
}>()

const suggestions = [
  '什么是Transformer架构？',
  '量子计算有哪些应用？',
  'CRISPR技术原理是什么？',
  '固态电池的优势有哪些？',
  '深度学习与机器学习有什么区别？',
]
</script>
