# Vue 3 前端重设计

## 概述

将 Deep Research Agent 前端从 Streamlit 完全迁移至 Vue 3 + Vite + TypeScript。

## 动机

- Streamlit 会话状态管理复杂，DOM 清理问题频发
- 自定义样式受限（通过 `unsafe_allow_html` 注入 CSS）
- SSE 流式数据需要 queue.Queue + threading.Event + st.rerun() 轮询
- 无法使用 npm 生态（marked、highlight.js 等）
- 难以扩展多页面功能（侧边栏导航、设置页、资料管理等）

## 决策

| 决策 | 选择 |
|------|------|
| 框架 | Vue 3 (Composition API) + TypeScript |
| 组件库 | Naive UI |
| 样式 | Tailwind CSS |
| 布局 | 侧边栏导航 |
| 状态管理 | Pinia |
| SSE 客户端 | 原生 EventSource |
| 后端 | FastAPI 完全不变 |

## 范围

**包含：**
- 全新 Vue 3 前端项目（frontend-vue/）
- 深度研究主页完整迁移（搜索、进度、报告、来源、取消）
- 侧边栏导航 + 预留路由（快速检索、资料管理、系统设置）
- 更新 start.sh 一键启动脚本

**不包含：**
- 快速检索/资料管理/设置页面具体实现
- 后端任何改动
- 暗色模式
