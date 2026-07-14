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
  'GraphRAG 主要解决什么问题？',
  'LangGraph 如何保存 Agent 的运行状态？',
  'Chroma 适合承担哪些向量存储任务？',
  'Qdrant 支持哪些向量检索能力？',
  'HotpotQA 中 supporting facts 有什么作用？',
]
</script>
