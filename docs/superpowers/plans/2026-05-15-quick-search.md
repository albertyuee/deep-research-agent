# Quick Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fast retrieval+summarization endpoint and a conversational chat UI at `/quick-search`, independent of the deep research pipeline.

**Architecture:** New `POST /api/v1/quick-search` endpoint bypasses LangGraph entirely — directly calls `HybridRetriever.search()` then one LLM call for summarization. Frontend `/quick-search` page is a chat interface with message history stored in a Pinia store.

**Tech Stack:** FastAPI (backend), Vue 3 + Naive UI + marked (frontend)

---

### Task 1: Backend — Quick Search API Endpoint

**Files:**
- Create: `backend/routers/quick_search.py`
- Read first: `research_agent/llm/factory.py`, `research_agent/graph.py:378-395`

- [ ] **Step 1: Create the quick search router**

Write `backend/routers/quick_search.py`:

```python
"""Quick Search API — fast retrieval + LLM summarization without the full agent pipeline."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.research_service import task_manager
from research_agent.llm.factory import create_llm_client
from research_agent.retrieval.vector_store import VectorStore
from research_agent.retrieval.bm25 import BM25Retriever
from research_agent.retrieval.hybrid import HybridRetriever
from config.settings import settings

router = APIRouter(prefix="/quick-search", tags=["quick-search"])

_SUMMARY_SYSTEM_PROMPT = """你是一个研究助手。基于以下检索到的文档片段，用中文简洁地回答用户的问题。

要求：
- 回答要准确、简洁，控制在 300 字以内
- 优先使用检索结果中的信息
- 如果检索结果不足以回答问题，如实告知用户
- 使用 Markdown 格式组织回答，包括要点列表"""

_vector_store: VectorStore | None = None
_bm25: BM25Retriever | None = None


def _get_hybrid() -> HybridRetriever:
    global _vector_store, _bm25
    if _vector_store is None:
        _vector_store = VectorStore()
    if _bm25 is None:
        _bm25 = BM25Retriever()
    return HybridRetriever(_vector_store, _bm25)


class QuickSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class QuickSearchResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


@router.post("", response_model=QuickSearchResponse)
async def quick_search(req: QuickSearchRequest):
    """Execute a fast hybrid search + LLM summarization."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    t0 = time.time()

    try:
        hybrid = _get_hybrid()
        results = hybrid.search(req.query, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {e}")

    sources = [
        {
            "chunk_id": r.chunk_id,
            "content": r.content,
            "score": r.combined_score,
            "metadata": r.metadata,
        }
        for r in results
    ]

    # Generate summary via LLM
    try:
        client = create_llm_client()
        context = "\n\n---\n\n".join(
            f"[来源 {i+1}] {r.content[:800]}"
            for i, r in enumerate(results[:5])
        )
        messages = [
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": f"检索结果：\n\n{context}\n\n用户问题：{req.query}\n\n请回答："},
        ]
        raw = await client.chat(messages, temperature=0.3, max_tokens=1024)
        summary = raw.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 摘要生成失败: {e}")

    elapsed_ms = int((time.time() - t0) * 1000)

    return QuickSearchResponse(
        success=True,
        data={
            "query": req.query,
            "summary": summary,
            "sources": sources,
            "elapsed_ms": elapsed_ms,
        },
    )
```

- [ ] **Step 2: Verify the code imports work**

```bash
cd /Users/albert/Desktop/Ai/测试/deep-research-agent && python3 -c "from backend.routers.quick_search import router; print('Import OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/routers/quick_search.py
git commit -m "feat: add quick search API endpoint (hybrid retrieval + LLM summary)"
```

---

### Task 2: Backend — Register Quick Search Router

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Read the current main.py**

Read `backend/main.py` to see the current router registration pattern.

- [ ] **Step 2: Add the quick search router import and registration**

In `backend/main.py`, add the import line:

```python
from backend.routers.quick_search import router as quick_search_router
```

And add the router registration line after the existing research router:

```python
app.include_router(quick_search_router, prefix="/api/v1")
```

The final `backend/main.py` should look like:

```python
"""FastAPI application entry point for Deep Research Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.research import router as research_router
from backend.routers.quick_search import router as quick_search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    yield


app = FastAPI(
    title="Deep Research Agent",
    description="Agentic RAG — autonomous query decomposition, adaptive retrieval, quality critique, and report synthesis",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router, prefix="/api/v1")
app.include_router(quick_search_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 3: Verify the app starts and new route is available**

```bash
cd /Users/albert/Desktop/Ai/测试/deep-research-agent
timeout 5 uvicorn backend.main:app --port 8000 2>&1 || true
sleep 2
curl -s http://localhost:8000/health
curl -s http://localhost:8000/docs | grep quick-search
```

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: register quick search router in main app"
```

---

### Task 3: Frontend — Chat API Layer and Pinia Store

**Files:**
- Create: `frontend-vue/src/api/chat.ts`
- Create: `frontend-vue/src/stores/chat.ts`

- [ ] **Step 1: Create src/api/chat.ts**

```typescript
const BASE = '/api/v1'

export interface QuickSearchResponse {
  success: boolean
  data: {
    query: string
    summary: string
    sources: Array<{
      chunk_id: string
      content: string
      score: number
      metadata: Record<string, unknown>
    }>
    elapsed_ms: number
  }
  error: string | null
}

export async function quickSearch(query: string, topK: number = 5): Promise<QuickSearchResponse['data']> {
  const resp = await fetch(`${BASE}/quick-search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  })
  if (!resp.ok) {
    throw new Error(`搜索失败: ${resp.status} ${resp.statusText}`)
  }
  const body: QuickSearchResponse = await resp.json()
  if (!body.success) {
    throw new Error(body.error || '搜索失败')
  }
  return body.data
}
```

- [ ] **Step 2: Create src/stores/chat.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { quickSearch } from '@/api/chat'
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

    const userMsg: ChatMessage = {
      id: `msg-${nextId++}`,
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }
    messages.value.push(userMsg)

    try {
      const data = await quickSearch(query)
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
      // Remove the user message on failure
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
```

- [ ] **Step 3: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add chat API layer and Pinia chat store"
```

---

### Task 4: Frontend — ChatMessage Component

**Files:**
- Create: `frontend-vue/src/components/chat/ChatMessage.vue`

- [ ] **Step 1: Create src/components/chat/ChatMessage.vue**

```vue
<template>
  <div class="flex mb-4" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
    <div
      class="max-w-[80%] rounded-2xl px-4 py-3"
      :class="msg.role === 'user'
        ? 'bg-gradient-to-r from-brand-700 to-purple-500 text-white'
        : 'bg-gray-100 text-gray-800'"
    >
      <!-- User message: plain text -->
      <p v-if="msg.role === 'user'" class="text-sm whitespace-pre-wrap">{{ msg.content }}</p>

      <!-- Assistant message: markdown summary + sources + meta -->
      <div v-else>
        <div class="markdown-body text-sm" v-html="renderedContent" />
        <div class="flex items-center gap-2 mt-2 text-xs text-gray-400">
          <span v-if="msg.elapsedMs">⏱ {{ (msg.elapsedMs / 1000).toFixed(1) }}s</span>
        </div>

        <!-- Sources -->
        <div v-if="msg.sources && msg.sources.length" class="mt-2">
          <n-collapse>
            <n-collapse-item title="📎 查看来源" name="sources">
              <div v-for="src in msg.sources" :key="src.chunk_id" class="source-card mb-2">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold text-gray-700">
                    {{ src.metadata?.doc_title || src.metadata?.source || src.chunk_id }}
                  </span>
                  <ScoreBadge :score="src.score" />
                </div>
                <p class="text-xs text-gray-500 line-clamp-3">{{ src.content?.slice(0, 300) }}</p>
              </div>
            </n-collapse-item>
          </n-collapse>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import ScoreBadge from '@/components/common/ScoreBadge.vue'
import type { ChatMessage } from '@/stores/chat'

const props = defineProps<{
  msg: ChatMessage
}>()

const renderedContent = computed(() => {
  return marked.parse(props.msg.content) as string
})
</script>
```

- [ ] **Step 2: Verify TypeScript compilation**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add ChatMessage component"
```

---

### Task 5: Frontend — ChatInput and SuggestionChips Components

**Files:**
- Create: `frontend-vue/src/components/chat/ChatInput.vue`
- Create: `frontend-vue/src/components/chat/SuggestionChips.vue`

- [ ] **Step 1: Create src/components/chat/ChatInput.vue**

```vue
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
```

- [ ] **Step 2: Create src/components/chat/SuggestionChips.vue**

```vue
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
      {{ q.slice(0, 40) }}{{ q.length > 40 ? '…' : '' }}
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
  '什么是Transformer架构？',
  '量子计算有哪些应用？',
  'CRISPR技术原理是什么？',
  '固态电池的优势有哪些？',
  '深度学习与机器学习有什么区别？',
]
</script>
```

- [ ] **Step 3: Verify TypeScript compilation and commit**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
git add -A && git commit -m "feat: add ChatInput and SuggestionChips components"
```

---

### Task 6: Frontend — ChatPanel and QuickSearchPage

**Files:**
- Create: `frontend-vue/src/components/chat/ChatPanel.vue`
- Modify: `frontend-vue/src/pages/QuickSearchPage.vue` (replace placeholder)

- [ ] **Step 1: Create src/components/chat/ChatPanel.vue**

```vue
<template>
  <div class="flex flex-col h-[calc(100vh-140px)]">
    <!-- Messages Area -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto px-2 py-4">
      <!-- Empty state -->
      <div v-if="store.messages.length === 0 && !store.isLoading" class="flex flex-col items-center justify-center h-full text-center">
        <div class="text-5xl mb-4">💬</div>
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
```

- [ ] **Step 2: Replace src/pages/QuickSearchPage.vue**

```vue
<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">⚡ 快速检索</h1>
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
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add ChatPanel and QuickSearchPage with chat UI"
```

---

### Task 7: Integration Test

**Files:**
- None (verification only)

- [ ] **Step 1: Start backend and verify the quick-search endpoint**

```bash
# Start backend
cd /Users/albert/Desktop/Ai/测试/deep-research-agent
uvicorn backend.main:app --port 8000 &
sleep 3

# Test quick search
curl -s -X POST http://localhost:8000/api/v1/quick-search \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是Transformer", "top_k": 3}' | python3 -m json.tool
```

Expected: Response contains `success: true`, `data.summary` (non-empty string), `data.sources` (array), `data.elapsed_ms` (number).

- [ ] **Step 2: Start frontend and verify the chat page loads**

```bash
# Start frontend
cd frontend-vue && npm run dev &
sleep 3

# Verify page loads
curl -s http://localhost:5173/quick-search | head -5
```

Expected: HTML response with `#app` div (SPA).

- [ ] **Step 3: Manual browser test**

Open `http://localhost:5173/quick-search` and verify:
1. Empty state shows welcome message + suggestion chips.
2. Clicking a suggestion chip fills the input.
3. Typing a question and pressing Enter sends it.
4. Loading indicator shows while waiting for response.
5. AI response appears with Markdown-formatted summary.
6. "查看来源" expander shows source cards with scores.
7. Sending another question adds to the history.
8. "清空对话" button clears all messages.
9. Sidebar navigation still works.

- [ ] **Step 4: Commit any fixes from integration testing**

```bash
git add -A && git commit -m "fix: integration test fixes for quick search"
```
