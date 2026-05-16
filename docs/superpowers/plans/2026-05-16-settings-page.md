# Settings Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a settings page at `/settings` with LLM/embedding/retrieval configuration forms, hot-reload to .env, and system info display.

**Architecture:** New `backend/routers/settings.py` provides GET/PATCH/config endpoints that read/write `config/.env` via python-dotenv. Frontend `/settings` page has grouped Naive UI form cards. LLM/embedding/retrieval params take effect immediately; infrastructure params require restart.

**Tech Stack:** FastAPI + python-dotenv (backend), Vue 3 + Naive UI (frontend)

---

## File Structure

```
backend/routers/settings.py           # NEW: Settings CRUD API
backend/main.py                       # MODIFY: Register settings router
config/settings.py                    # MODIFY: Add reload_settings()
frontend-vue/src/api/settings.ts      # NEW: Settings HTTP calls
frontend-vue/src/stores/settings.ts   # MODIFY: Extend placeholder
frontend-vue/src/components/settings/
  SettingsSection.vue                 # NEW: Grouped form card wrapper
  SystemInfo.vue                      # NEW: System stats card
frontend-vue/src/pages/SettingsPage.vue  # MODIFY: Replace placeholder
```

---

### Task 1: Backend — Settings API

**Files:**
- Create: `backend/routers/settings.py`
- Modify: `config/settings.py` (add reload function)
- Read first: `config/settings.py`

- [ ] **Step 1: Add reload_settings() to config/settings.py**

In `config/settings.py`, add after the `settings = Settings()` line:

```python
def reload_settings():
    """Reload settings from .env after changes. Rebuild the singleton."""
    global settings
    settings = Settings()
```

- [ ] **Step 2: Create backend/routers/settings.py**

```python
"""Settings management API — read, update, hot-reload configuration."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv, dotenv_values

from config.settings import settings, reload_settings

router = APIRouter(prefix="/settings", tags=["settings"])

ENV_FILE = Path(__file__).parent.parent.parent / "config" / ".env"


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return ""
    return key[:3] + "***" + key[-4:]


def _get_llm_settings() -> dict:
    return {
        "provider": settings.llm.provider,
        "model": settings.llm.model,
        "api_key": _mask_key(settings.llm.api_key),
        "base_url": settings.llm.base_url,
        "temperature": settings.llm.temperature,
        "max_tokens": settings.llm.max_tokens,
    }


def _get_embedding_settings() -> dict:
    return {
        "mode": settings.embedding.mode,
        "model": settings.embedding.model,
        "device": settings.embedding.device,
        "api_base_url": settings.embedding.api_base_url,
        "api_key": _mask_key(settings.embedding.api_key),
    }


def _get_retrieval_settings() -> dict:
    return {
        "top_k": settings.retrieval.top_k,
        "max_retries": settings.retrieval.max_retries,
        "critique_threshold": settings.retrieval.critique_threshold,
        "rrf_k": settings.retrieval.rrf_k,
        "vector_backend": settings.retrieval.vector_backend,
    }


def _write_env(updates: dict[str, str]) -> None:
    """Write key-value pairs to the .env file, preserving existing keys."""
    load_dotenv(ENV_FILE)
    current = dict(dotenv_values(ENV_FILE))
    current.update(updates)

    lines = []
    for k, v in current.items():
        lines.append(f"{k}={v}")

    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")


@router.get("")
async def get_settings():
    return {
        "success": True,
        "data": {
            "llm": _get_llm_settings(),
            "embedding": _get_embedding_settings(),
            "retrieval": _get_retrieval_settings(),
        },
    }


@router.patch("")
async def update_settings(body: dict):
    """Partially update settings. Writes to .env and hot-reloads.

    Request format: { "llm": { "temperature": 0.5 }, "retrieval": { "top_k": 8 } }
    """
    env_updates: dict[str, str] = {}
    updated_keys: list[str] = []

    # Map JSON paths to ENV keys
    path_map = {
        "llm.provider": ("LLM_PROVIDER", str),
        "llm.model": ("LLM_MODEL", str),
        "llm.api_key": ("LLM_API_KEY", str),
        "llm.base_url": ("LLM_BASE_URL", str),
        "llm.temperature": ("LLM_TEMPERATURE", str),
        "llm.max_tokens": ("LLM_MAX_TOKENS", str),
        "embedding.mode": ("EMBEDDING_MODE", str),
        "embedding.model": ("EMBEDDING_MODEL", str),
        "embedding.device": ("EMBEDDING_DEVICE", str),
        "embedding.api_base_url": ("EMBEDDING_API_BASE_URL", str),
        "embedding.api_key": ("EMBEDDING_API_KEY", str),
        "retrieval.top_k": ("RETRIEVAL_TOP_K", str),
        "retrieval.max_retries": ("RETRIEVAL_MAX_RETRIES", str),
        "retrieval.critique_threshold": ("RETRIEVAL_CRITIQUE_THRESHOLD", str),
        "retrieval.rrf_k": ("RETRIEVAL_RRF_K", str),
        "retrieval.vector_backend": ("RETRIEVAL_VECTOR_BACKEND", str),
    }

    for section in ["llm", "embedding", "retrieval"]:
        if section in body:
            for key, value in body[section].items():
                path = f"{section}.{key}"
                if path in path_map:
                    env_key, _ = path_map[path]
                    # Skip masked API keys (contain ***)
                    if "api_key" in key and value and "***" in str(value):
                        continue
                    env_updates[env_key] = str(value)
                    updated_keys.append(path)

    if not env_updates:
        raise HTTPException(status_code=400, detail="No valid settings to update")

    _write_env(env_updates)
    reload_settings()

    return {
        "success": True,
        "data": {
            "updated": updated_keys,
            "need_restart": False,
        },
    }


@router.get("/system-info")
async def get_system_info():
    try:
        from research_agent.retrieval.vector_store import VectorStore
        vs = VectorStore()
        chroma_chunks = vs.count
    except Exception:
        chroma_chunks = 0

    return {
        "success": True,
        "data": {
            "chroma_chunks": chroma_chunks,
            "version": "0.1.0",
        },
    }
```

- [ ] **Step 3: Verify import and commit**

```bash
cd /Users/albert/Desktop/Ai/测试/deep-research-agent
python3 -c "from backend.routers.settings import router; print('Import OK')"
# Ensure python-dotenv is available
pip install python-dotenv -q 2>/dev/null
git add backend/routers/settings.py config/settings.py
git commit -m "feat: add settings API with hot-reload (GET/PATCH/config)"
```

---

### Task 2: Backend — Register Settings Router

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add import and registration in backend/main.py**

After the existing router imports:
```python
from backend.routers.settings import router as settings_router
```

After the existing `app.include_router` lines:
```python
app.include_router(settings_router, prefix="/api/v1")
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "feat: register settings router"
```

---

### Task 3: Frontend — Settings API + Store

**Files:**
- Create: `frontend-vue/src/api/settings.ts`
- Modify: `frontend-vue/src/stores/settings.ts` (extend placeholder)

- [ ] **Step 1: Create src/api/settings.ts**

```typescript
const BASE = '/api/v1'

export interface LLMSettings {
  provider: string
  model: string
  api_key: string
  base_url: string
  temperature: number
  max_tokens: number
}

export interface EmbeddingSettings {
  mode: string
  model: string
  api_key: string
  device: string
  api_base_url: string
}

export interface RetrievalSettings {
  top_k: number
  max_retries: number
  critique_threshold: number
  rrf_k: number
  vector_backend: string
}

export interface SettingsData {
  llm: LLMSettings
  embedding: EmbeddingSettings
  retrieval: RetrievalSettings
}

export interface SystemInfo {
  chroma_chunks: number
  version: string
}

export async function fetchSettings(): Promise<SettingsData> {
  const resp = await fetch(`${BASE}/settings`)
  if (!resp.ok) throw new Error(`获取配置失败: ${resp.status}`)
  const body = await resp.json()
  return body.data
}

export async function updateSettings(
  patch: Partial<{ llm: Partial<LLMSettings>; embedding: Partial<EmbeddingSettings>; retrieval: Partial<RetrievalSettings> }>
): Promise<{ updated: string[]; need_restart: boolean }> {
  const resp = await fetch(`${BASE}/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  if (!resp.ok) throw new Error(`保存失败: ${resp.status}`)
  const body = await resp.json()
  return body.data
}

export async function fetchSystemInfo(): Promise<SystemInfo> {
  const resp = await fetch(`${BASE}/settings/system-info`)
  if (!resp.ok) throw new Error(`获取系统信息失败: ${resp.status}`)
  const body = await resp.json()
  return body.data
}
```

- [ ] **Step 2: Rewrite src/stores/settings.ts**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchSettings, updateSettings, fetchSystemInfo } from '@/api/settings'
import type { SettingsData, SystemInfo } from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<SettingsData | null>(null)
  const systemInfo = ref<SystemInfo | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const successMsg = ref<string | null>(null)

  const hasSettings = computed(() => settings.value !== null)

  async function loadSettings(): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      const [s, info] = await Promise.all([fetchSettings(), fetchSystemInfo()])
      settings.value = s
      systemInfo.value = info
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载配置失败'
    } finally {
      isLoading.value = false
    }
  }

  async function saveSettings(patch: Parameters<typeof updateSettings>[0]): Promise<void> {
    isSaving.value = true
    error.value = null
    successMsg.value = null
    try {
      const result = await updateSettings(patch)
      await loadSettings()
      successMsg.value = result.need_restart
        ? '配置已保存，部分修改需重启后生效'
        : '配置已保存并生效'
      setTimeout(() => { successMsg.value = null }, 5000)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '保存失败'
    } finally {
      isSaving.value = false
    }
  }

  return { settings, systemInfo, isLoading, isSaving, error, successMsg, hasSettings, loadSettings, saveSettings }
})
```

- [ ] **Step 3: Verify and commit**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
git add -A && git commit -m "feat: add settings API layer and Pinia store"
```

---

### Task 4: Frontend — SettingsPage with Form Sections

**Files:**
- Create: `frontend-vue/src/components/settings/SettingsSection.vue`
- Create: `frontend-vue/src/components/settings/SystemInfo.vue`
- Modify: `frontend-vue/src/pages/SettingsPage.vue` (replace placeholder)

- [ ] **Step 1: Create SettingsSection.vue**

```vue
<template>
  <n-card :bordered="false" size="small" class="mb-4 settings-card">
    <template #header>
      <span class="font-semibold text-gray-700">{{ title }}</span>
    </template>
    <slot />
  </n-card>
</template>

<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<style scoped>
.settings-card { border-radius: 14px; border: 1px solid #f3f4f6; }
</style>
```

- [ ] **Step 2: Create SystemInfo.vue**

```vue
<template>
  <SettingsSection title="系统信息">
    <n-spin :show="loading">
      <div v-if="info" class="grid grid-cols-2 gap-4 text-sm">
        <div class="flex justify-between"><span class="text-gray-500">ChromaDB Chunks</span><span class="font-semibold">{{ info.chroma_chunks }}</span></div>
        <div class="flex justify-between"><span class="text-gray-500">版本</span><span class="font-semibold">{{ info.version }}</span></div>
      </div>
    </n-spin>
  </SettingsSection>
</template>

<script setup lang="ts">
import SettingsSection from './SettingsSection.vue'
import type { SystemInfo } from '@/stores/settings'

defineProps<{ info: SystemInfo | null; loading: boolean }>()
</script>
```

- [ ] **Step 3: Replace SettingsPage.vue**

```vue
<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">⚙️ 系统设置</h1>
        <p class="text-sm text-gray-400">配置 LLM、嵌入模型和检索参数</p>
      </div>
      <n-button type="primary" :loading="store.isSaving" @click="onSave">
        <template #icon><n-icon><save-outline /></n-icon></template>
        保存配置
      </n-button>
    </div>

    <n-spin :show="store.isLoading">
      <n-alert v-if="store.error" type="error" :bordered="false" class="mb-4" @close="store.error = null">
        {{ store.error }}
      </n-alert>
      <n-alert v-if="store.successMsg" type="success" :bordered="false" class="mb-4">
        {{ store.successMsg }}
      </n-alert>

      <div v-if="store.settings">
        <!-- LLM -->
        <SettingsSection title="LLM 配置">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">提供商</label>
              <n-select v-model:value="form.llm.provider" :options="llmProviders" size="small" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">模型</label>
              <n-input v-model:value="form.llm.model" size="small" />
            </div>
            <div class="col-span-2">
              <label class="text-xs text-gray-500 mb-1 block">API Key</label>
              <n-input v-model:value="form.llm.api_key" type="password" show-password-on="click" size="small" placeholder="留空则不修改" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">Temperature: {{ form.llm.temperature }}</label>
              <n-slider v-model:value="form.llm.temperature" :min="0" :max="2" :step="0.1" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">Max Tokens</label>
              <n-input-number v-model:value="form.llm.max_tokens" size="small" :min="256" :max="32768" />
            </div>
          </div>
        </SettingsSection>

        <!-- Embedding -->
        <SettingsSection title="嵌入模型">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">模式</label>
              <n-radio-group v-model:value="form.embedding.mode">
                <n-radio value="local">本地</n-radio>
                <n-radio value="api">API</n-radio>
              </n-radio-group>
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">模型</label>
              <n-input v-model:value="form.embedding.model" size="small" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">API 地址</label>
              <n-input v-model:value="form.embedding.api_base_url" size="small" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">API Key</label>
              <n-input v-model:value="form.embedding.api_key" type="password" show-password-on="click" size="small" placeholder="留空则不修改" />
            </div>
          </div>
        </SettingsSection>

        <!-- Retrieval -->
        <SettingsSection title="检索配置">
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">Top-K</label>
              <n-input-number v-model:value="form.retrieval.top_k" size="small" :min="1" :max="50" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">最大重试</label>
              <n-input-number v-model:value="form.retrieval.max_retries" size="small" :min="0" :max="10" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">相似度阈值: {{ form.retrieval.critique_threshold }}</label>
              <n-slider v-model:value="form.retrieval.critique_threshold" :min="0.3" :max="0.95" :step="0.05" />
            </div>
          </div>
        </SettingsSection>
      </div>

      <SystemInfo :info="store.systemInfo" :loading="store.isLoading" />
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { NIcon } from 'naive-ui'
import { SaveOutline } from '@vicons/ionicons5'
import { useSettingsStore } from '@/stores/settings'
import SettingsSection from '@/components/settings/SettingsSection.vue'
import SystemInfo from '@/components/settings/SystemInfo.vue'

const store = useSettingsStore()

const llmProviders = [
  { label: 'SiliconFlow', value: 'siliconflow' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Qwen (通义千问)', value: 'qwen' },
]

const form = reactive({
  llm: { provider: 'siliconflow', model: '', api_key: '', base_url: '', temperature: 0.3, max_tokens: 4096 },
  embedding: { mode: 'api', model: '', api_key: '', device: 'cpu', api_base_url: '' },
  retrieval: { top_k: 5, max_retries: 3, critique_threshold: 0.6, rrf_k: 60, vector_backend: 'chroma' },
})

watch(() => store.settings, (s) => {
  if (s) {
    Object.assign(form.llm, s.llm)
    Object.assign(form.embedding, s.embedding)
    Object.assign(form.retrieval, s.retrieval)
  }
}, { immediate: true })

onMounted(() => { store.loadSettings() })

function onSave() {
  store.saveSettings({
    llm: form.llm,
    embedding: form.embedding,
    retrieval: form.retrieval,
  })
}
</script>
```

- [ ] **Step 4: Verify and commit**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
git add -A && git commit -m "feat: add SettingsPage with LLM/embedding/retrieval forms and system info"
```

---

### Task 5: Integration Test

- [ ] **Step 1: Verify TypeScript and API**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
cd /Users/albert/Desktop/Ai/测试/deep-research-agent
uvicorn backend.main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/api/v1/settings | python3 -m json.tool
curl -s -X PATCH http://localhost:8000/api/v1/settings -H "Content-Type: application/json" -d '{"retrieval":{"top_k":10}}' | python3 -m json.tool
curl -s http://localhost:8000/api/v1/settings/system-info | python3 -m json.tool
pkill -f uvicorn
```

Expected: GET returns masked config, PATCH updates top_k and writes .env, system-info returns chunk count.

- [ ] **Step 2: Commit fixes if any**

```bash
git add -A && git commit -m "fix: integration test fixes for settings page"
```
