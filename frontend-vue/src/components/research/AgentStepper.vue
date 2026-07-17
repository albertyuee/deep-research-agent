<template>
  <n-card :bordered="false" size="small" class="mb-4 stepper-card">
    <div class="stepper">
      <template v-for="(key, i) in keys" :key="key">
        <div class="stepper-step">
          <div class="stepper-dot" :class="store.phaseStates[key]">
            {{ dotIcon(key) }}
          </div>
          <span class="stepper-label" :class="{ active: store.phaseStates[key] !== 'waiting' }">
            {{ store.phaseLabels[key] }}
          </span>
        </div>
        <div
          v-if="i < keys.length - 1"
          class="stepper-connector"
          :class="{ done: store.phaseStates[key] === 'complete' }"
        />
      </template>
    </div>

    <div v-if="store.currentDetail" class="mt-2">
      <n-alert
        v-if="store.isCancelled"
        type="warning"
        :bordered="false"
      >
        {{ store.currentDetail }}
      </n-alert>
      <n-alert
        v-else-if="store.error"
        type="error"
        :bordered="false"
      >
        {{ store.error }}
      </n-alert>
      <n-alert
        v-else-if="store.currentStep === 'done'"
        type="success"
        :bordered="false"
      >
        {{ store.currentDetail }}
      </n-alert>
      <n-alert
        v-else
        type="info"
        :bordered="false"
      >
        {{ store.currentDetail }}
      </n-alert>
    </div>

    <n-progress
      v-if="store.currentStep && store.currentStep !== 'done'"
      class="mt-3"
      type="line"
      :percentage="Math.round(Math.min(store.progressValue * 100, 98))"
      :indicator-placement="'inside'"
      :height="20"
      :border-radius="4"
      processing
    />
    <n-progress
      v-else-if="store.currentStep === 'done'"
      class="mt-3"
      type="line"
      :percentage="100"
      status="success"
      :indicator-placement="'inside'"
      :height="20"
      :border-radius="4"
    />

    <div v-if="store.startedAt" class="text-xs text-gray-400 mt-1">
      {{ store.isRunning ? '已用时' : '总用时' }}: {{ elapsedSeconds }}s
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useResearchStore } from '@/stores/research'

const store = useResearchStore()
const keys = ['decomposition', 'retrieval', 'critique', 'synthesis']
const now = ref(Date.now())
let timer: ReturnType<typeof setInterval> | null = null

const elapsedSeconds = computed(() => {
  if (!store.startedAt) return 0
  const end = store.isRunning ? now.value : (store.finishedAt || now.value)
  return Math.max(0, Math.floor((end - store.startedAt) / 1000))
})

onMounted(() => {
  timer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})

function dotIcon(key: string): string {
  const state = store.phaseStates[key]
  if (state === 'complete') return '\u2713'
  if (state === 'error') return '\u2717'
  const iconMap: Record<string, string> = {
    decomposition: '1',
    retrieval: '2',
    critique: '3',
    synthesis: '4',
  }
  return iconMap[key] || '?'
}
</script>

<style scoped>
.stepper-card {
  background: linear-gradient(135deg, #f8fafc 0%, #f5f3ff 100%);
  border-radius: 14px;
  border: 1px solid #ede9fe;
}
</style>
