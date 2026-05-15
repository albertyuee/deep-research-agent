<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">快速检索</h1>
        <p class="text-sm text-gray-400">即时检索 + AI 摘要，秒级响应</p>
      </div>
      <n-button
        v-if="store.messages.length > 0"
        text
        size="small"
        @click="store.clearHistory()"
      >
        <template #icon><n-icon><trash-outline /></n-icon></template>
        清空对话
      </n-button>
    </div>

    <n-card :bordered="false" class="chat-container">
      <ChatPanel />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { TrashOutline } from '@vicons/ionicons5'
import { useChatStore } from '@/stores/chat'
import ChatPanel from '@/components/chat/ChatPanel.vue'

const store = useChatStore()
</script>

<style scoped>
.chat-container {
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 2px 16px rgba(124, 58, 237, 0.04);
}
</style>
