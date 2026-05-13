## Why

当前项目虽然 factory.py 中已预留 SiliconFlow 的 Provider 映射，但默认配置以 Qwen 为主，硅基流动的接入不够直观。硅基流动作为国内主流的 LLM API 平台，提供低价、高速的模型调用服务，需要将其作为一等 Provider 完善配置，同时补全项目 README 文档以便快速上手和面试展示。

## What Changes

- 新增 `config/.env` 文件，默认配置硅基流动 API Key
- 更新 `config/settings.py`：硅基流动默认模型设为 `Qwen/Qwen3-8B`
- 更新 `research_agent/llm/factory.py`：硅基流动默认 base_url 确认正确
- 新增 `config/.env.example`：增加硅基流动注册链接和模型推荐注释
- 完善 `README.md`：补全架构图、快速开始指南、API 文档、面试展示要点、与 sql-agent-kit 对比表

## Capabilities

### New Capabilities
- `siliconflow-config`: 硅基流动 LLM Provider 的一等配置支持，包括默认模型、base_url、env 配置

### Modified Capabilities
<!-- 无已有 spec 需要修改 -->

## Impact

- 修改文件：`config/settings.py`, `config/.env.example`, `research_agent/llm/factory.py`, `README.md`
- 新增文件：`config/.env`
- 无 API 变更，无 breaking changes
