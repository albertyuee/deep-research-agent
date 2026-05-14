## Why

当前 Streamlit 前端只展示 high-level 的进度概要（阶段时间线 + 一句话状态文字），用户无法看到 Agent 内部的详细运行情况。当 Agent 执行较慢或出错时，用户完全不知道底层发生了什么——哪个 LLM 调用耗时最长？检索返回了什么内容？质量评分为什么是那个分数？这导致调试困难和用户体验差。

## What Changes

- 新增**实时事件日志面板**：按时间顺序展示所有 SSE 事件，附带关键数据摘要，默认折叠，可展开查看详细 payload
- 增强**各阶段详细信息展示**：
  - 拆解阶段：显示每个子问题的推荐策略和选择理由
  - 检索阶段：显示返回结果数量、最高相似度分数、结果内容预览
  - 评估阶段：显示评分推理文字（reasoning 字段）
  - 合成阶段：显示报告生成进度
- 增加**阶段耗时统计**：每个阶段（拆解/检索/评估/合成）的独立耗时
- 增加**重试历史展示**：如果有检索重试，显示每次重试的原因和查询改写内容
- 所有新增日志区域默认折叠，不影响正常使用体验；需要时可以展开查看

## Capabilities

### New Capabilities
- `frontend-event-log`: 实时 SSE 事件日志面板，按时间线展示所有事件，支持展开查看完整 payload
- `frontend-step-details`: 每个 Agent 步骤的详细信息展示（检索结果预览、评分推理、耗时统计等）

### Modified Capabilities
<!-- 无现有 specs 需要修改 -->

## Impact

- 仅修改 `frontend/components/agent_progress.py`，无需修改后端或 Agent 核心逻辑
- 利用已有 SSE 事件流数据，不增加 API 调用
- Streamlit 组件架构不变，通过 `st.expander` 实现折叠/展开
