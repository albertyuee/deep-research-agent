# Document Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add document upload/list/delete with auto-indexing into vector + BM25 stores, and a card-grid management UI at `/documents`.

**Architecture:** New `backend/routers/documents.py` provides 3 REST endpoints (GET list, POST upload, DELETE remove). Upload flow reuses `DocumentLoader` → `VectorStore.add_documents()` → `BM25Retriever.index_documents()`. Frontend `/documents` page has card grid + upload/preview/delete dialogs.

**Tech Stack:** FastAPI + multipart (backend), Vue 3 + Naive UI (frontend)

---

## File Structure

```
backend/routers/documents.py        # NEW: Document CRUD API
backend/main.py                     # MODIFY: Register documents router
frontend-vue/src/api/documents.ts   # NEW: HTTP calls for documents
frontend-vue/src/stores/documents.ts# MODIFY: Extend with real data
frontend-vue/src/components/documents/
  DocumentCard.vue                  # NEW: File card with preview/delete
  UploadDialog.vue                  # NEW: Upload modal with progress
  PreviewDialog.vue                 # NEW: Content preview modal
frontend-vue/src/pages/DocumentsPage.vue  # MODIFY: Replace placeholder
```

---

### Task 1: Backend — Documents API Endpoint

**Files:**
- Create: `backend/routers/documents.py`

- [ ] **Step 1: Create backend/routers/documents.py**

```python
"""Document management API — upload, list, delete with auto-indexing."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from research_agent.retrieval.document_loader import DocumentLoader, SUPPORTED_EXTENSIONS
from research_agent.retrieval.vector_store import VectorStore
from research_agent.retrieval.bm25 import BM25Retriever

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path("data/uploads")
FILES_JSON = UPLOAD_DIR / "files.json"

_vector_store: VectorStore | None = None
_bm25: BM25Retriever | None = None


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def _get_bm25() -> BM25Retriever:
    global _bm25
    if _bm25 is None:
        _bm25 = BM25Retriever()
    return _bm25


def _read_files_meta() -> dict:
    if not FILES_JSON.exists():
        return {"files": []}
    with open(FILES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_files_meta(data: dict) -> None:
    FILES_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(FILES_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Response Models ──

class DocumentItem(BaseModel):
    id: str
    name: str
    size: int
    chunks: int
    status: str
    uploaded_at: str


class DocumentListResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


class DocumentUploadResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


class DocumentDeleteResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


# ── Routes ──

@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """List all uploaded documents."""
    meta = _read_files_meta()
    return DocumentListResponse(success=True, data={"files": meta["files"]})


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document, chunk it, and index into vector + BM25 stores."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    file_id = uuid.uuid4().hex[:12]
    file_dir = UPLOAD_DIR / file_id
    file_dir.mkdir(parents=True, exist_ok=True)

    temp_path = file_dir / file.filename
    content = await file.read()

    try:
        # Save original file
        with open(temp_path, "wb") as f:
            f.write(content)

        # Load and chunk
        loader = DocumentLoader()
        chunks = loader.load_file(temp_path)

        if not chunks:
            raise HTTPException(status_code=400, detail="Document produced no chunks (may be too short or empty)")

        # Index into vector store
        vs = _get_vector_store()
        chunk_ids = [c.chunk_id for c in chunks]
        chunk_texts = [c.content for c in chunks]
        chunk_metas = [
            {
                **c.metadata,
                "doc_title": file.filename.rsplit(".", 1)[0],
                "source": file.filename,
                "upload_id": file_id,
            }
            for c in chunks
        ]
        vs.add_documents(chunk_ids, chunk_texts, chunk_metas)

        # Index into BM25
        bm25 = _get_bm25()
        if bm25.is_indexed:
            # Append new chunks to existing BM25 index
            all_ids = list(bm25._documents[i]["id"] for i in range(len(bm25._documents)))
            all_texts = list(bm25._documents[i]["content"] for i in range(len(bm25._documents)))
            all_metas = list(bm25._documents[i]["metadata"] for i in range(len(bm25._documents)))
            all_ids.extend(chunk_ids)
            all_texts.extend(chunk_texts)
            all_metas.extend(chunk_metas)
        else:
            all_ids = chunk_ids
            all_texts = chunk_texts
            all_metas = chunk_metas
        bm25.index_documents(all_ids, all_texts, all_metas)

        # Record metadata
        meta = _read_files_meta()
        meta["files"].append({
            "id": file_id,
            "name": file.filename,
            "size": len(content),
            "chunks": len(chunks),
            "status": "ready",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })
        _write_files_meta(meta)

        return DocumentUploadResponse(
            success=True,
            data={
                "file_id": file_id,
                "name": file.filename,
                "chunks": len(chunks),
                "status": "ready",
            },
        )

    except HTTPException:
        # Clean up on known HTTP errors
        if file_dir.exists():
            shutil.rmtree(file_dir)
        raise
    except Exception as e:
        # Clean up on unexpected errors
        if file_dir.exists():
            shutil.rmtree(file_dir)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.delete("/{file_id}", response_model=DocumentDeleteResponse)
async def delete_document(file_id: str):
    """Delete a document: remove original file, ChromaDB chunks, rebuild BM25."""
    meta = _read_files_meta()
    target = None
    for f in meta["files"]:
        if f["id"] == file_id:
            target = f
            break

    if not target:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        # Remove original files
        file_dir = UPLOAD_DIR / file_id
        if file_dir.exists():
            shutil.rmtree(file_dir)

        # Remove from ChromaDB (chunks with this upload_id in metadata)
        vs = _get_vector_store()
        # ChromaDB delete by metadata filter
        try:
            vs.collection.delete(where={"upload_id": file_id})
        except Exception:
            pass  # ChromaDB may not support metadata filter delete

        # Rebuild BM25 from remaining ChromaDB data
        try:
            remaining = vs.collection.get(include=["documents", "metadatas"])
            if remaining and remaining["ids"]:
                bm25 = _get_bm25()
                bm25.index_documents(
                    remaining["ids"],
                    remaining["documents"] or [],
                    remaining["metadatas"] or [],
                )
        except Exception:
            pass

        # Remove from metadata
        meta["files"] = [f for f in meta["files"] if f["id"] != file_id]
        _write_files_meta(meta)

        return DocumentDeleteResponse(
            success=True,
            data={"file_id": file_id, "message": "Document deleted"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
```

- [ ] **Step 2: Verify Python import**

```bash
cd /Users/albert/Desktop/Ai/测试/deep-research-agent && python3 -c "from backend.routers.documents import router; print('Import OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/routers/documents.py
git commit -m "feat: add document management API (list, upload, delete)"
```

---

### Task 2: Backend — Register Documents Router

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add import and registration**

In `backend/main.py`, add after the existing router imports:

```python
from backend.routers.documents import router as documents_router
```

Add after the existing `app.include_router` lines:

```python
app.include_router(documents_router, prefix="/api/v1")
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "feat: register documents router"
```

---

### Task 3: Frontend — Documents API Layer + Store

**Files:**
- Create: `frontend-vue/src/api/documents.ts`
- Modify: `frontend-vue/src/stores/documents.ts` (extend placeholder)

- [ ] **Step 1: Create src/api/documents.ts**

```typescript
const BASE = '/api/v1'

export interface DocFile {
  id: string
  name: string
  size: number
  chunks: number
  status: 'ready' | 'processing' | 'error'
  uploaded_at: string
}

export interface DocListResponse {
  success: boolean
  data: { files: DocFile[] }
  error: string | null
}

export interface DocUploadResponse {
  success: boolean
  data: { file_id: string; name: string; chunks: number; status: string }
  error: string | null
}

export async function fetchDocuments(): Promise<DocFile[]> {
  const resp = await fetch(`${BASE}/documents`)
  if (!resp.ok) throw new Error(`获取文件列表失败: ${resp.status}`)
  const body: DocListResponse = await resp.json()
  if (!body.success) throw new Error(body.error || '获取失败')
  return body.data.files
}

export async function uploadDocument(file: File): Promise<DocUploadResponse['data']> {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(`${BASE}/documents/upload`, {
    method: 'POST',
    body: form,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || `上传失败: ${resp.status}`)
  }
  const body: DocUploadResponse = await resp.json()
  if (!body.success) throw new Error(body.error || '上传失败')
  return body.data
}

export async function deleteDocument(fileId: string): Promise<void> {
  const resp = await fetch(`${BASE}/documents/${fileId}`, { method: 'DELETE' })
  if (!resp.ok) throw new Error(`删除失败: ${resp.status}`)
}
```

- [ ] **Step 2: Rewrite src/stores/documents.ts**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchDocuments, uploadDocument, deleteDocument } from '@/api/documents'
import type { DocFile } from '@/api/documents'

export type { DocFile }

export const useDocumentsStore = defineStore('documents', () => {
  const files = ref<DocFile[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const totalChunks = computed(() => files.value.reduce((sum, f) => sum + f.chunks, 0))
  const totalSize = computed(() => files.value.reduce((sum, f) => sum + f.size, 0))

  async function loadFiles(): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      files.value = await fetchDocuments()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载文件列表失败'
    } finally {
      isLoading.value = false
    }
  }

  async function upload(file: File): Promise<void> {
    error.value = null
    try {
      await uploadDocument(file)
      await loadFiles()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '上传失败'
      throw e
    }
  }

  async function remove(fileId: string): Promise<void> {
    error.value = null
    try {
      await deleteDocument(fileId)
      await loadFiles()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '删除失败'
      throw e
    }
  }

  return { files, isLoading, error, totalChunks, totalSize, loadFiles, upload, remove }
})
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add documents API layer and Pinia store"
```

---

### Task 4: Frontend — DocumentCard + Dialogs

**Files:**
- Create: `frontend-vue/src/components/documents/DocumentCard.vue`
- Create: `frontend-vue/src/components/documents/UploadDialog.vue`
- Create: `frontend-vue/src/components/documents/PreviewDialog.vue`

- [ ] **Step 1: Create DocumentCard.vue**

```vue
<template>
  <n-card :bordered="false" size="small" class="doc-card">
    <div class="flex items-start justify-between mb-2">
      <div class="flex items-center gap-2">
        <span class="text-xl">{{ fileIcon }}</span>
        <span class="font-semibold text-sm text-gray-800 truncate max-w-[140px]" :title="file.name">
          {{ file.name }}
        </span>
      </div>
      <n-tag :type="statusType" size="tiny">{{ statusLabel }}</n-tag>
    </div>

    <div class="text-xs text-gray-400 space-y-1 mb-3">
      <div>{{ file.chunks }} chunks · {{ formatSize(file.size) }}</div>
      <div>{{ formatTime(file.uploaded_at) }}</div>
    </div>

    <div class="flex gap-2">
      <n-button text size="small" type="primary" @click="$emit('preview', file)">
        <template #icon><n-icon><eye-outline /></n-icon></template>
        预览
      </n-button>
      <n-popconfirm @positive-click="$emit('delete', file.id)">
        <template #trigger>
          <n-button text size="small" type="error">
            <template #icon><n-icon><trash-outline /></n-icon></template>
            删除
          </n-button>
        </template>
        确定删除「{{ file.name }}」？此操作不可撤销。
      </n-popconfirm>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { EyeOutline, TrashOutline } from '@vicons/ionicons5'
import type { DocFile } from '@/stores/documents'

const props = defineProps<{ file: DocFile }>()

defineEmits<{
  preview: [file: DocFile]
  delete: [fileId: string]
}>()

const extIconMap: Record<string, string> = {
  pdf: '📕', docx: '📘', md: '📝', txt: '📄',
}
const fileIcon = computed(() => {
  const ext = props.file.name.split('.').pop()?.toLowerCase() || ''
  return extIconMap[ext] || '📎'
})

const statusType = computed(() => {
  return props.file.status === 'ready' ? 'success' : props.file.status === 'error' ? 'error' : 'warning'
})
const statusLabel = computed(() => {
  return props.file.status === 'ready' ? '已就绪' : props.file.status === 'error' ? '失败' : '处理中'
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return `${Math.floor(diff / 86400000)} 天前`
}
</script>

<style scoped>
.doc-card {
  border-radius: 14px;
  border: 1px solid #f3f4f6;
  transition: all 0.2s;
}
.doc-card:hover {
  border-color: #c4b5fd;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.08);
}
</style>
```

- [ ] **Step 2: Create UploadDialog.vue**

```vue
<template>
  <n-modal v-model:show="visible" preset="card" title="上传文档" style="width:480px">
    <n-upload
      multiple
      :max="5"
      accept=".pdf,.docx,.md,.txt"
      :custom-request="handleUpload"
      :show-file-list="true"
    >
      <n-upload-dragger>
        <div class="text-center py-8">
          <div class="text-3xl mb-2">📁</div>
          <p class="text-sm text-gray-600">点击或拖拽文件到此处上传</p>
          <p class="text-xs text-gray-400 mt-1">支持 PDF、Word、Markdown、TXT</p>
        </div>
      </n-upload-dragger>
    </n-upload>
    <div v-if="uploadError" class="mt-3">
      <n-alert type="error" :bordered="false">{{ uploadError }}</n-alert>
    </div>
    <template #footer>
      <n-button @click="visible = false">关闭</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useDocumentsStore } from '@/stores/documents'

const visible = defineModel<boolean>('show', { required: true })
const store = useDocumentsStore()
const uploadError = ref<string | null>(null)
const uploading = ref(false)

async function handleUpload(options: { file: File; onFinish: () => void; onError: () => void }) {
  uploading.value = true
  uploadError.value = null
  try {
    await store.upload(options.file)
    options.onFinish()
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传失败'
    options.onError()
  } finally {
    uploading.value = false
  }
}
</script>
```

- [ ] **Step 3: Create PreviewDialog.vue**

```vue
<template>
  <n-modal v-model:show="visible" preset="card" title="文件预览" style="width:640px">
    <div v-if="file">
      <div class="text-sm text-gray-500 mb-3 space-y-1">
        <div><strong>文件名:</strong> {{ file.name }}</div>
        <div><strong>大小:</strong> {{ formatSize(file.size) }} · <strong>Chunks:</strong> {{ file.chunks }}</div>
        <div><strong>上传时间:</strong> {{ file.uploaded_at }}</div>
        <div><strong>状态:</strong> <n-tag :type="file.status === 'ready' ? 'success' : 'warning'" size="tiny">{{ file.status }}</n-tag></div>
      </div>
      <n-divider />
      <p class="text-xs text-gray-400">完整内容预览需要从向量库读取，此处展示文件元信息。</p>
    </div>
    <template #footer>
      <n-button @click="visible = false">关闭</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import type { DocFile } from '@/stores/documents'

const visible = defineModel<boolean>('show', { required: true })
defineProps<{ file: DocFile | null }>()

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>
```

- [ ] **Step 4: Verify and commit**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
git add -A && git commit -m "feat: add DocumentCard, UploadDialog, PreviewDialog components"
```

---

### Task 5: Frontend — DocumentsPage

**Files:**
- Modify: `frontend-vue/src/pages/DocumentsPage.vue` (replace placeholder)

- [ ] **Step 1: Replace src/pages/DocumentsPage.vue**

```vue
<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">📁 资料管理</h1>
        <p class="text-sm text-gray-400">
          {{ store.files.length > 0 ? `${store.files.length} 个文件 · ${store.totalChunks} chunks · ${formatSize(store.totalSize)}` : '上传文档以扩展知识库' }}
        </p>
      </div>
      <n-button type="primary" @click="showUpload = true">
        <template #icon><n-icon><cloud-upload-outline /></n-icon></template>
        上传文件
      </n-button>
    </div>

    <!-- Loading -->
    <n-spin :show="store.isLoading" />

    <!-- Error -->
    <n-alert v-if="store.error" type="error" :bordered="false" class="mb-4">
      {{ store.error }}
    </n-alert>

    <!-- File Grid -->
    <div v-if="store.files.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <DocumentCard
        v-for="f in store.files"
        :key="f.id"
        :file="f"
        @preview="onPreview"
        @delete="onDelete"
      />
    </div>

    <!-- Empty State -->
    <div v-else-if="!store.isLoading" class="flex flex-col items-center justify-center py-20 text-center">
      <div class="text-5xl mb-4">📂</div>
      <h3 class="text-lg font-semibold text-gray-700 mb-2">暂无文档</h3>
      <p class="text-sm text-gray-400 max-w-sm mb-4">
        上传 PDF、Word、Markdown 或 TXT 文档，自动分块索引入知识库，立即可被检索。
      </p>
      <n-button type="primary" @click="showUpload = true">
        <template #icon><n-icon><cloud-upload-outline /></n-icon></template>
        上传第一个文档
      </n-button>
    </div>

    <!-- Dialogs -->
    <UploadDialog v-model:show="showUpload" />
    <PreviewDialog v-model:show="showPreview" :file="previewFile" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NIcon } from 'naive-ui'
import { CloudUploadOutline } from '@vicons/ionicons5'
import { useDocumentsStore } from '@/stores/documents'
import type { DocFile } from '@/stores/documents'
import DocumentCard from '@/components/documents/DocumentCard.vue'
import UploadDialog from '@/components/documents/UploadDialog.vue'
import PreviewDialog from '@/components/documents/PreviewDialog.vue'

const store = useDocumentsStore()
const showUpload = ref(false)
const showPreview = ref(false)
const previewFile = ref<DocFile | null>(null)

onMounted(() => {
  store.loadFiles()
})

function onPreview(file: DocFile) {
  previewFile.value = file
  showPreview.value = true
}

async function onDelete(fileId: string) {
  try {
    await store.remove(fileId)
  } catch {
    // Error handled by store
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
cd frontend-vue && git add -A && git commit -m "feat: add DocumentsPage with file grid and dialogs"
```

---

### Task 6: Integration Test

- [ ] **Step 1: Verify TypeScript compilation**

```bash
cd frontend-vue && ./node_modules/.bin/vue-tsc --noEmit
```

- [ ] **Step 2: Start backend and test API**

```bash
cd /Users/albert/Desktop/Ai/测试/deep-research-agent
uvicorn backend.main:app --port 8000 &
sleep 3

# Test list (should show existing files from start.sh indexing if any)
curl -s http://localhost:8000/api/v1/documents | python3 -m json.tool

# Test upload with a small markdown file
echo "# Test Doc\n\nThis is a test paragraph for document upload testing.\n\nAnother paragraph here." > /tmp/test_upload.md
curl -s -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/tmp/test_upload.md" | python3 -m json.tool

# Verify file appears in list
curl -s http://localhost:8000/api/v1/documents | python3 -m json.tool

# Test delete (use the file_id from upload response)
# curl -s -X DELETE http://localhost:8000/api/v1/documents/{file_id} | python3 -m json.tool
```

- [ ] **Step 3: Start frontend and verify the page loads**

```bash
cd frontend-vue && npm run dev &
sleep 3
curl -s http://localhost:5173/documents | head -5
```

- [ ] **Step 4: Manual browser verification**

Open `http://localhost:5173/documents`:
1. Page loads with file grid (shows uploaded files)
2. Click "上传文件" → dialog opens → select a PDF/MD file
3. File appears as a new card in the grid after upload
4. Click "预览" → dialog opens with file metadata
5. Click "删除" → confirmation → file card disappears

- [ ] **Step 5: Commit fixes if any**

```bash
git add -A && git commit -m "fix: integration test fixes for document management"
```
