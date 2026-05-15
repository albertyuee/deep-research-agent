<template>
  <span class="score-badge" :class="colorClass">{{ score.toFixed(2) }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ score: number }>()

const colorClass = computed(() => {
  if (props.score >= 0.7) return 'pass'
  if (props.score >= 0.4) return 'warn'
  return 'fail'
})
</script>

<style scoped>
.score-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}
.score-badge.pass { background: #d1fae5; color: #065f46; }
.score-badge.warn { background: #fef3c7; color: #92400e; }
.score-badge.fail { background: #fee2e2; color: #991b1b; }
</style>
