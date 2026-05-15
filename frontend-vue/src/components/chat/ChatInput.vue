<template>
  <div class="flex items-end gap-2 pt-3 border-t border-gray-100">
    <n-input
      v-model:value="text"
      type="textarea"
      placeholder="输入问题，快速检索..."
      :autosize="{ minRows: 1, maxRows: 4 }"
      :disabled="disabled"
      round
      size="large"
      @keydown.enter="handleEnter"
    />
    <n-button
      type="primary"
      size="large"
      :disabled="!text.trim() || disabled"
      :loading="disabled"
      @click="emitSend"
    >
      <template #icon><n-icon><send-outline /></n-icon></template>
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NIcon } from 'naive-ui'
import { SendOutline } from '@vicons/ionicons5'

defineProps<{
  disabled: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const text = ref('')

function handleEnter(e: KeyboardEvent) {
  if (!e.shiftKey) {
    e.preventDefault()
    emitSend()
  }
}

function emitSend() {
  const trimmed = text.value.trim()
  if (trimmed) {
    emit('send', trimmed)
    text.value = ''
  }
}
</script>
