<template>
  <div class="flex flex-col h-[calc(100vh-140px)]">
    <!-- Messages Area -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto px-2 py-4">
      <!-- Empty state -->
      <div v-if="store.messages.length === 0 && !store.isLoading" class="flex flex-col items-center justify-center h-full text-center">
        <div class="text-5xl mb-4">⚡</div>
        <h3 class="text-lg font-semibold text-gray-700 mb-2">快速检索</h3>
        <p class="text-sm text-gray-400 max-w-sm">
          基于知识库的即时问答，秒级响应。<br>适合快速查找和简单问题。
        </p>
      </div>

      <!-- Messages -->
      <ChatMessage
        v-for="msg in store.messages"
        :key="msg.id"
        :msg="msg"
      />

      <!-- Loading indicator -->
      <div v-if="store.isLoading" class="flex justify-start mb-4">
        <div class="bg-gray-100 rounded-2xl px-4 py-3">
          <div class="flex gap-1">
            <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms" />
            <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms" />
            <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms" />
          </div>
        </div>
      </div>

      <!-- Error -->
      <n-alert v-if="store.error" type="error" :bordered="false" class="mt-2" @close="store.error = null">
        {{ store.error }}
      </n-alert>
    </div>

    <!-- Input Area -->
    <div class="px-2 pb-2">
      <SuggestionChips
        v-if="store.messages.length === 0"
        :disabled="store.isLoading"
        @select="onSend"
      />
      <ChatInput
        :disabled="store.isLoading"
        @send="onSend"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'
import SuggestionChips from './SuggestionChips.vue'

const store = useChatStore()
const messagesContainer = ref<HTMLElement>()

watch(
  () => store.messages.length,
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  },
)

function onSend(text: string) {
  store.sendMessage(text)
}
</script>
