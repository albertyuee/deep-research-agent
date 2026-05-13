## Context

当前 LLM 配置以 Qwen（阿里云百炼）为主要 Provider，settings.py 中已有 `siliconflow` 选项，factory.py 中已映射 `base_url`。但缺少实际可用的 `.env` 文件，默认模型选用不明确，硅基流动作为低成本高速推理平台的定位未在配置层面体现。

## Goals / Non-Goals

**Goals:**
- 硅基流动作为默认 Provider，开箱即用
- `.env` 文件提供可用的默认 API Key（用户可替换）
- `.env.example` 包含硅基流动注册引导和模型推荐
- README 覆盖快速开始、架构说明、面试展示要点
- settings.py 中硅基流动默认模型设为性价比最优的 `Qwen/Qwen3-8B`

**Non-Goals:**
- 不新增 Provider 类型（硅基流动走 OpenAI 兼容 API，已有 `OpenAIClient`）
- 不修改 Agent 业务逻辑

## Decisions

### 1. 默认 Provider：siliconflow

**选择**：默认 provider 从 `qwen` 改为 `siliconflow`
**理由**：硅基流动无需阿里云企业认证，个人开发者注册即用，2000 万免费 token 额度，更适合开源项目演示

### 2. 默认模型：Qwen/Qwen3-8B

**选择**：硅基流动默认模型设为 `Qwen/Qwen3-8B`
**替代考虑**：`deepseek-ai/DeepSeek-V3`（更强但更贵）、`Qwen/Qwen2.5-7B-Instruct`（旧版）
**理由**：Qwen3-8B 在成本（￥0.5/百万 token）和推理能力之间平衡最优，且用户有通义千问经验

### 3. 默认维度：1536

**选择**：默认 Embedding 维度从 1024 改为 1536
**理由**：硅基流动的 Embedding 模型 `BAAI/bge-large-zh-v1.5` 输出 1024 维，但硅基流动也支持 `BAAI/bge-m3`（1024 维）等多款。保持 1024 不变以兼容。

实际上保持现有 1024 维不变，因为 bge-large-zh-v1.5 输出 1024 维。

## Risks / Trade-offs

- **[风险] API Key 泄露** → `.env` 中的 key 为占位符，README 明确说明需替换
- **[风险] 免费额度耗尽** → README 列出备用 Provider（Qwen/OpenAI）
