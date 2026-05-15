# 资料管理功能

## 概述

新增资料管理功能，支持上传/列表/删除文档，自动分块并索引入向量库和 BM25。

## 决策

| 决策 | 选择 |
|------|------|
| 存储 | `data/uploads/` + `files.json` |
| 索引 | 复用 DocumentLoader → VectorStore + BM25 |
| 前端 | 卡片网格 + 上传/预览/删除弹窗 |

## 范围

- 后端 `GET/POST/DELETE /api/v1/documents` 端点
- 前端 `/documents` 页面（卡片网格 + 弹窗）
- 自动分块 + 向量索引 + BM25 索引
