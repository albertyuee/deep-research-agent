<template>
  <div class="mb-5">
    <n-card :bordered="false" class="search-card">
      <n-input
        v-model:value="inputText"
        type="textarea"
        placeholder="输入你的研究问题，例如：人工智能在医疗影像和药物研发中的应用有什么区别？"
        :autosize="{ minRows: 2, maxRows: 4 }"
        :disabled="isRunning"
        size="large"
        round
        @keydown.enter.ctrl="emitSubmit"
      />
      <div class="flex items-center gap-3 mt-3">
        <n-button
          type="primary"
          size="large"
          :disabled="!inputText.trim() || isRunning"
          :loading="isRunning"
          @click="emitSubmit"
        >
          <template #icon><n-icon><rocket-outline /></n-icon></template>
          {{ isRunning ? '研究中...' : '开始研究' }}
        </n-button>
        <n-button
          v-if="isRunning"
          type="error"
          size="large"
          secondary
          @click="$emit('stop')"
        >
          <template #icon><n-icon><stop-circle-outline /></n-icon></template>
          停止
        </n-button>
      </div>

      <div v-if="!isRunning" class="flex flex-wrap gap-2 mt-3">
        <n-tag
          v-for="(ex, i) in examples"
          :key="i"
          :bordered="true"
          type="info"
          size="small"
          class="cursor-pointer hover:border-brand-700 hover:text-brand-700 transition-colors"
          @click="selectExample(ex)"
        >
          {{ ex.slice(0, 35) }}{{ ex.length > 35 ? '…' : '' }}
        </n-tag>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NIcon } from 'naive-ui'
import { RocketOutline, StopCircleOutline } from '@vicons/ionicons5'

defineProps<{
  isRunning: boolean
}>()

const emit = defineEmits<{
  submit: [query: string]
  stop: []
}>()

const examples = [
  '人工智能在医疗影像和药物研发中的应用有什么区别？',
  'Transformer架构相比LSTM在自然语言处理中有哪些优势？',
  '量子计算的发展对现代密码学构成多大的威胁？',
  'CRISPR基因编辑技术在遗传病治疗中的前景和伦理挑战是什么？',
  '固态电池技术相比传统锂电池的核心突破点在哪里？',
]

const inputText = ref(examples[0])

function emitSubmit() {
  const q = inputText.value.trim()
  if (q) {
    emit('submit', q)
  }
}

function selectExample(text: string) {
  inputText.value = text
}
</script>

<style scoped>
.search-card {
  background: linear-gradient(135deg, #ffffff 0%, #fafbff 100%);
  border-radius: 16px;
  box-shadow: 0 2px 16px rgba(124, 58, 237, 0.06);
}
</style>
