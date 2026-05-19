<template>
  <div class="mb-5">
    <n-card :bordered="false" class="search-card">
      <div class="flex items-start gap-3">
        <div class="flex-1">
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
        </div>
        <div class="flex items-center gap-2 flex-shrink-0">
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
      </div>

      <!-- 网络搜索开关 -->
      <div class="flex items-center gap-3 mt-3">
        <n-switch
          v-model:value="enableWebSearch"
          :disabled="isRunning"
          size="small"
        />
        <span class="text-xs text-gray-500">
          联网搜索
          <span class="text-gray-400 ml-1">
            {{ enableWebSearch ? '已开启：将获取实时信息辅助研究' : '已关闭：仅使用本地知识库' }}
          </span>
        </span>
      </div>

      <div v-if="!isRunning" class="flex flex-wrap gap-2 mt-3">
        <span
          v-for="(ex, i) in examples"
          :key="i"
          class="example-chip"
          @click="selectExample(ex)"
        >
          💡 {{ ex.slice(0, 30) }}{{ ex.length > 30 ? '…' : '' }}
        </span>
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
  submit: [query: string, enableWebSearch: boolean]
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
const enableWebSearch = ref(false)

function emitSubmit() {
  const q = inputText.value.trim()
  if (q) {
    emit('submit', q, enableWebSearch.value)
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

.example-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border-radius: 24px;
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border: 1px solid #e9d5ff;
  color: #7c3aed;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.example-chip:hover {
  background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%);
  border-color: #c4b5fd;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.15);
  color: #6d28d9;
}
</style>
