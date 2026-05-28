import { defineStore } from 'pinia'
import { ref } from 'vue'
import { quickSearch } from '@/api/chat'
import type { ChatHistoryItem } from '@/api/chat'
import type { Source } from './research'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  elapsedMs?: number
  timestamp: number
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  let nextId = 1

  async function sendMessage(query: string): Promise<void> {
    error.value = null
    isLoading.value = true

    const history: ChatHistoryItem[] = messages.value
      .slice(-8)
      .map((msg) => ({ role: msg.role, content: msg.content }))

    const userMsg: ChatMessage = {
      id: `msg-${nextId++}`,
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }
    messages.value.push(userMsg)

    try {
      const data = await quickSearch(query, 5, history)
      const assistantMsg: ChatMessage = {
        id: `msg-${nextId++}`,
        role: 'assistant',
        content: data.summary,
        sources: data.sources as Source[],
        elapsedMs: data.elapsed_ms,
        timestamp: Date.now(),
      }
      messages.value.push(assistantMsg)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '搜索请求失败'
      messages.value.pop()
    } finally {
      isLoading.value = false
    }
  }

  function clearHistory(): void {
    messages.value = []
    error.value = null
  }

  return { messages, isLoading, error, sendMessage, clearHistory }
})
