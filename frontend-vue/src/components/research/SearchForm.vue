<template>
  <div class="mb-5">
    <n-card :bordered="false" class="search-card">
      <div class="search-input-row">
        <n-input
          v-model:value="inputText"
          class="query-input"
          type="textarea"
          placeholder="输入一个需要调查、比较或多步推理的研究问题"
          :autosize="{ minRows: 2, maxRows: 5 }"
          :disabled="isRunning"
          size="large"
          round
          @keydown.enter.ctrl="emitSubmit"
          @keydown.enter.meta="emitSubmit"
        />
        <div class="search-actions">
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
          <span v-else class="shortcut-hint">⌘/Ctrl + Enter</span>
        </div>
      </div>

      <div class="form-section">
        <div class="section-heading">
          <span class="section-title">研究模式</span>
          <span class="section-hint">选择 Agent 如何拆解和执行子问题</span>
        </div>
        <div class="mode-grid" role="radiogroup" aria-label="研究模式">
          <button
            v-for="mode in modes"
            :key="mode.value"
            type="button"
            role="radio"
            class="mode-card"
            :class="{ selected: researchMode === mode.value }"
            :aria-label="mode.label"
            :aria-checked="researchMode === mode.value"
            :disabled="isRunning"
            @click="researchMode = mode.value"
          >
            <span class="mode-card-top">
              <span class="mode-icon" aria-hidden="true">{{ mode.icon }}</span>
              <span class="mode-title">{{ mode.label }}</span>
              <span v-if="mode.recommended" class="recommended-tag">推荐</span>
              <span class="mode-check" aria-hidden="true">{{ researchMode === mode.value ? '✓' : '' }}</span>
            </span>
            <span class="mode-description">{{ mode.description }}</span>
          </button>
        </div>

        <button
          v-if="researchMode !== 'parallel'"
          type="button"
          class="advanced-toggle"
          :aria-expanded="showAdvanced"
          :disabled="isRunning"
          @click="showAdvanced = !showAdvanced"
        >
          <span>{{ showAdvanced ? '收起高级设置' : '高级设置' }}</span>
          <span aria-hidden="true">{{ showAdvanced ? '⌃' : '⌄' }}</span>
        </button>
        <div v-if="researchMode !== 'parallel' && showAdvanced" class="advanced-panel">
          <div>
            <div class="advanced-label">最大跳数</div>
            <div class="advanced-description">限制依赖链深度，复杂问题建议使用 3–5 跳。</div>
          </div>
          <n-input-number
            v-model:value="maxHops"
            aria-label="最大跳数"
            :disabled="isRunning"
            :min="1"
            :max="8"
            size="small"
            style="width: 96px"
          />
        </div>
      </div>

      <div class="option-row">
        <n-switch
          v-model:value="enableWebSearch"
          aria-label="联网搜索"
          :disabled="isRunning"
          size="small"
        />
        <div>
          <div class="option-title">联网搜索</div>
          <div class="option-description">
            {{ enableWebSearch ? '已开启，将补充实时网络信息。' : '已关闭，仅使用本地知识库。' }}
          </div>
        </div>
      </div>

      <div v-if="!isRunning" class="examples-section">
        <div class="examples-heading">
          <span class="section-title">示例问题</span>
          <button
            v-if="examples.length > collapsedExampleCount"
            type="button"
            class="examples-toggle"
            :aria-expanded="showAllExamples"
            @click="showAllExamples = !showAllExamples"
          >
            {{ showAllExamples ? '收起' : '查看更多' }}
          </button>
        </div>
        <div class="examples-list">
          <button
            v-for="(example, index) in visibleExamples"
            :key="index"
            type="button"
            class="example-chip"
            @click="selectExample(example)"
          >
            <span aria-hidden="true">💡</span>
            <span>{{ example }}</span>
          </button>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NIcon } from 'naive-ui'
import { RocketOutline, StopCircleOutline } from '@vicons/ionicons5'
import type { ResearchMode } from '@/api/research'

defineProps<{
  isRunning: boolean
}>()

const emit = defineEmits<{
  submit: [query: string, enableWebSearch: boolean, researchMode: ResearchMode, maxHops: number]
  stop: []
}>()

const modes: Array<{
  value: ResearchMode
  label: string
  icon: string
  description: string
  recommended?: boolean
}> = [
  {
    value: 'auto',
    label: '自动规划',
    icon: '✦',
    description: '自动判断并列或依赖步骤，适合大多数问题。',
    recommended: true,
  },
  {
    value: 'parallel',
    label: '并列研究',
    icon: '⇶',
    description: '独立检索多个角度，适合对比、盘点与汇总。',
  },
  {
    value: 'multihop',
    label: '多跳推理',
    icon: '↳',
    description: '逐步传递实体与事实，适合因果链和实体追踪。',
  },
]

const examples = [
  'GraphRAG、LangGraph、Haystack 和 LlamaIndex 在深度研究系统中可以分别承担什么职责？',
  '如果要构建支持元数据过滤和混合检索的 RAG，Chroma 与 Qdrant 应该如何选择？',
  'HotpotQA 的 supporting facts 机制可以怎样改进多跳推理的可解释性和评估方式？',
  '如何结合 GraphRAG 的图结构检索与 LangGraph 的有状态工作流构建多跳研究 Agent？',
  'Haystack 与 LlamaIndex 在数据接入、检索编排和 Agent 扩展方面有哪些差异？',
]

const collapsedExampleCount = 3
const inputText = ref(examples[0])
const enableWebSearch = ref(false)
const researchMode = ref<ResearchMode>('auto')
const maxHops = ref(3)
const showAdvanced = ref(false)
const showAllExamples = ref(false)

const visibleExamples = computed(() => (
  showAllExamples.value ? examples : examples.slice(0, collapsedExampleCount)
))

function emitSubmit() {
  const query = inputText.value.trim()
  if (query) {
    emit('submit', query, enableWebSearch.value, researchMode.value, maxHops.value)
  }
}

function selectExample(text: string) {
  inputText.value = text
}
</script>

<style scoped>
.search-card {
  background: linear-gradient(135deg, #ffffff 0%, #fafbff 100%);
  border: 1px solid #ede9fe;
  border-radius: 18px;
  box-shadow: 0 8px 30px rgba(91, 33, 182, 0.07);
}

.search-input-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 14px;
}

.query-input {
  min-width: 0;
}

.search-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
}

.shortcut-hint {
  color: #a1a1aa;
  font-size: 0.68rem;
  text-align: center;
}

.form-section {
  margin-top: 18px;
}

.section-heading,
.examples-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 9px;
}

.section-title {
  color: #374151;
  font-size: 0.8rem;
  font-weight: 700;
}

.section-hint {
  color: #9ca3af;
  font-size: 0.72rem;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.mode-card {
  position: relative;
  min-width: 0;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.84);
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.mode-card:hover:not(:disabled) {
  border-color: #c4b5fd;
  box-shadow: 0 5px 16px rgba(124, 58, 237, 0.08);
  transform: translateY(-1px);
}

.mode-card:focus-visible {
  outline: 3px solid rgba(124, 58, 237, 0.22);
  outline-offset: 2px;
}

.mode-card.selected {
  border-color: #8b5cf6;
  background: linear-gradient(135deg, #faf5ff, #f5f3ff);
  box-shadow: inset 0 0 0 1px rgba(124, 58, 237, 0.12);
}

.mode-card:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.mode-card-top {
  display: flex;
  align-items: center;
  gap: 7px;
}

.mode-icon {
  color: #7c3aed;
  font-size: 1rem;
  font-weight: 800;
}

.mode-title {
  color: #374151;
  font-size: 0.82rem;
  font-weight: 700;
}

.recommended-tag {
  padding: 1px 6px;
  border-radius: 999px;
  background: #ede9fe;
  color: #6d28d9;
  font-size: 0.62rem;
  font-weight: 700;
}

.mode-check {
  margin-left: auto;
  color: #7c3aed;
  font-weight: 800;
}

.mode-description {
  display: block;
  margin-top: 7px;
  color: #8b8f98;
  font-size: 0.7rem;
  line-height: 1.5;
}

.advanced-toggle,
.examples-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 9px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #7c3aed;
  cursor: pointer;
  font-size: 0.72rem;
}

.advanced-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 9px;
  padding: 11px 12px;
  border: 1px solid #ede9fe;
  border-radius: 10px;
  background: #faf9ff;
}

.advanced-label,
.option-title {
  color: #4b5563;
  font-size: 0.78rem;
  font-weight: 650;
}

.advanced-description,
.option-description {
  margin-top: 2px;
  color: #9ca3af;
  font-size: 0.69rem;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 15px;
  padding-top: 14px;
  border-top: 1px solid #f1f1f5;
}

.examples-section {
  margin-top: 14px;
}

.examples-heading {
  margin-bottom: 8px;
}

.examples-toggle {
  margin-top: 0;
}

.examples-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.example-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  gap: 5px;
  padding: 7px 12px;
  border: 1px solid #e9d5ff;
  border-radius: 999px;
  background: #faf5ff;
  color: #7c3aed;
  cursor: pointer;
  font-size: 0.72rem;
  font-weight: 500;
  line-height: 1.35;
  text-align: left;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.example-chip:hover {
  border-color: #c4b5fd;
  background: #f3e8ff;
}

.example-chip:focus-visible,
.advanced-toggle:focus-visible,
.examples-toggle:focus-visible {
  outline: 2px solid #8b5cf6;
  outline-offset: 2px;
}

@media (max-width: 820px) {
  .mode-grid {
    grid-template-columns: 1fr;
  }

  .mode-description {
    margin-left: 24px;
  }
}

@media (max-width: 640px) {
  .search-input-row {
    grid-template-columns: 1fr;
  }

  .search-actions {
    flex-direction: row;
    align-items: center;
  }

  .search-actions :deep(.n-button) {
    flex: 1;
  }

  .shortcut-hint {
    display: none;
  }

  .section-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }

  .advanced-panel {
    align-items: flex-start;
  }

  .examples-list {
    display: grid;
    grid-template-columns: 1fr;
  }

  .example-chip {
    border-radius: 12px;
  }
}
</style>
