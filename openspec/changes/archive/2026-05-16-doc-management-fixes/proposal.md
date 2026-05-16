# 资料管理 Bug 修复

## 修复列表

1. **n-spin 一直转圈** — `DocumentsPage.vue` 中 `<n-spin>` 为独立标签未包裹内容，改为包裹 file grid 和 empty state
2. **现有文档不显示** — `GET /documents` 仅读 files.json，增加 ChromaDB 扫描自动发现已索引文档
3. **上传报 [object Object]** — Naive UI `customRequest` 中 `options.file` 是 `UploadFileInfo`，真实 File 在 `options.file.file`；FastAPI 422 detail 为数组需格式化
4. **上传 PDF 413 错误** — SiliconFlow 嵌入 API 拒绝超大文本，`DocumentLoader` 增加 `max_chunk_chars=300` 限制超长段落切分；`EmbeddingService` batch_size 降至 8
