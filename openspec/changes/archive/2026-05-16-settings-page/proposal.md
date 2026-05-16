# 系统设置页面

## 概述

实现 `/settings` 页面的系统配置功能，支持修改 LLM、嵌入模型、检索参数并热重载生效，展示系统状态信息。

## 功能

- LLM 配置（提供商/模型/API Key/Temperature/Max Tokens）
- 嵌入模型配置（本地/API/模型/API地址）
- 检索配置（Top-K/最大重试/相似度阈值）
- 系统信息（ChromaDB 统计/版本）
- 热重载：PATCH → 写 .env → reload_settings()
