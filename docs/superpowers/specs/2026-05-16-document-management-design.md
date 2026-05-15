# 资料管理功能 — 设计文档

## 概述

新增资料管理功能，支持上传 PDF/DOCX/MD/TXT 文档，自动分块并索引入向量库和 BM25 索引，使上传的资料立即可被深度研究和快速检索使用。

## 动机

- 当前知识库只能通过 `start.sh` 的示例文档索引，用户无法添加自己的资料
- 已有 `DocumentLoader`（PDF/DOCX/MD/TXT）和 `VectorStore.add_documents()` 基础设施
- 需要独立的文件管理页面 + 上传 API

## 目标

- 上传文档 → 自动分块 → 入向量库 + BM25，立即可检索
- 文件列表展示（名称、大小、chunk 数、状态、时间）
- 支持全文预览和删除
- 原始文件保留在 `data/uploads/`

## 后端 API

### GET /api/v1/documents

返回文件列表，从 `data/uploads/files.json` 读取。

```json
{
  "success": true,
  "data": {
    "files": [
      {
        "id": "uuid-1",
        "name": "transformer论文.pdf",
        "size": 2048000,
        "chunks": 15,
        "status": "ready",
        "uploaded_at": "2026-05-16T10:00:00Z"
      }
    ]
  }
}
```

### POST /api/v1/documents/upload

**Request:** `multipart/form-data`, field name `file`

**Flow:**
```
1. 接收文件 → 验证格式（.pdf/.docx/.md/.txt）
2. 保存到 data/uploads/{file_id}/{original_name}
3. DocumentLoader.load_file() → chunks
4. VectorStore.add_documents(chunks)
5. BM25Retriever.index_documents(chunks)
6. 写入 files.json
7. 返回 { file_id, name, chunks, status: "ready" }
```

上传失败时清理已写入的文件和 chunks。

### DELETE /api/v1/documents/{file_id}

**Flow:**
```
1. 从 files.json 读取文件信息
2. 从 ChromaDB 删除所有匹配 source_path 的 chunks
3. 重建 BM25 索引（从 ChromaDB 当前数据）
4. 删除 data/uploads/{file_id}/
5. 从 files.json 移除记录
```

## 元数据存储

`data/uploads/files.json`:
```json
{
  "files": [
    {
      "id": "uuid-1",
      "name": "original.pdf",
      "size": 2048000,
      "chunks": 15,
      "status": "ready",
      "uploaded_at": "2026-05-16T10:00:00Z"
    }
  ]
}
```

## 前端

### 页面布局

`/documents` — 资料管理页面

- 顶部：标题 + 「上传文件」按钮
- 主体：文件卡片网格（grid 3-4 列）
- 每张卡片：文件名、chunks 数、大小、状态标签、上传时间、预览/删除按钮
- 空状态：引导文字

### 组件

| 组件 | 说明 |
|------|------|
| `DocumentsPage.vue` | 页面主体 |
| `DocumentCard.vue` | 文件卡片 |
| `UploadDialog.vue` | 上传弹窗（拖拽 + 进度） |
| `PreviewDialog.vue` | 内容预览弹窗 |

### 交互

- 上传 → 弹出对话框 → 选择文件 → 进度条 → 卡片出现
- 预览 → 弹出对话框 → 文件元信息 + 内容片段
- 删除 → 确认弹窗 → 删除文件 + 卡片消失

## 不在范围内

- 多知识库/集合管理
- 批量上传
- 文件内容在线编辑
- ChromaDB 和 BM25 的改动（复用现有接口）
