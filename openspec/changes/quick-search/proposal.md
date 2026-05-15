# 快速检索功能

## 概述

在深度研究基础上新增快速检索功能，绕过 LangGraph 流水线，直接进行混合检索 + LLM 摘要，实现秒级响应的对话式问答。

## 动机

- 深度研究慢（2-5 分钟），用户需要快速查找 + 简单总结
- 检索基础设施（向量 + BM25 + RRF）本身很快（<0.5s），瓶颈在 LLM 调用链
- 需要独立的对话式界面，与深度研究形成快/慢双模式

## 决策

| 决策 | 选择 |
|------|------|
| 协议 | 同步 HTTP（非 SSE） |
| 检索 | 复用 HybridRetriever |
| 摘要 | 一次 LLM 调用，检索结果作为 context |
| 前端 | 对话式 Chat UI |
| 历史 | 前端 Pinia store（会话内，不持久化） |

## 范围

**包含：**
- 新 `POST /api/v1/quick-search` 端点
- 对话式前端（ChatPanel / ChatMessage / ChatInput / SuggestionChips）
- 来源引用展示

**不包含：**
- 多轮对话上下文
- 对话历史持久化
- 深度研究流程改动
