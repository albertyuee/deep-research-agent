## Context

当前前端使用 Streamlit 的两栏布局（左侧 1/3 进度面板 + 右侧 2/3 报告面板）。所有进度信息堆在左侧一个长列表中，通过 `st.expander` 折叠。阶段时间线用 markdown 字符串模拟（`~~删除线~~` 表示完成、`**粗体**` 表示当前）。样式完全依赖 Streamlit 默认主题，无自定义 CSS。

**技术约束**：
- Streamlit 的渲染模型是声明式的，每次 rerun 都会重新执行整个脚本
- 自定义 CSS 只能通过 `st.markdown("<style>...</style>", unsafe_allow_html=True)` 注入
- `st.status` 是 Streamlit 1.28+ 的原生步骤指示器组件，支持 `running`/`complete`/`error` 状态
- `st.sidebar` 是 Streamlit 内置的侧边栏区域，适合放置辅助信息
- `st.form` 可以捕获 Enter 键提交，但会阻止增量交互（表单内所有组件在提交前不会触发 rerun）

## Goals / Non-Goals

**Goals:**
- 用 `st.status` 原生组件替代手工阶段时间线，提供清晰的步骤状态可视化
- 右侧报告区增加空状态引导页，消除首次加载时的空白
- 评分和状态信息增加颜色编码（绿=通过、红=失败、橙=警告）
- 将事件日志、耗时统计等辅助信息移至 `st.sidebar`，精简左侧主面板
- 添加自定义 CSS 提升视觉层次（卡片、阴影、间距）
- 输入区增加可点击的示例查询，支持 Enter 提交
- 进度条改为接入后端上报的真实百分比

**Non-Goals:**
- 不改动 Streamlit 整体两栏布局（`[1, 2]` 比例保持不变）
- 不引入新的 Python 依赖或前端框架
- 不修改后端 SSE 事件的核心字段结构（仅新增可选的 `progress` 字段）
- 不实现深色/浅色主题切换（Streamlit 的 theme 配置属于用户设置层面）
- 不改造移动端响应式布局（Streamlit 自身在移动端能力有限）

## Decisions

### 1. 阶段指示器：`st.status` 替代 markdown 模拟

**方案**：使用 `st.status("阶段名称", state="running"|"complete"|"error")` 创建原生步骤指示器，在 `render_progress_panel()` 中根据 `current_step` 状态动态创建 4 个 status 容器。

**替代方案**：自定义 HTML/CSS 步骤条 → 不采用，因为工作量更大且与 Streamlit 风格不一致。

**注意**：`st.status` 的状态一旦设置为 `complete` 就无法再变回 `running`，所以需要在整个研究任务期间保持 status 对象的引用并逐步更新。由于 Streamlit 的 rerun 特性，需要在 `st.session_state` 中追踪每个阶段的状态。

实现方式：每个阶段用一个状态变量跟踪：
```
st.session_state.phase_states = {
    "decomposition": "waiting" | "running" | "complete" | "error",
    "retrieval": ...,
    "critique": ...,
    "synthesis": ...
}
```

在 `render_progress_panel()` 中遍历所有阶段，用 `st.status` 渲染。但这有一个问题：`st.status` 是上下文管理器，多次调用会创建多个实例。折中方案是只在当前活跃阶段使用 `st.status`，已完成阶段显示简单的 ✅ 标记。

最终决定：采用混合方案 — 用 CSS 自定义步骤条（比 markdown 技巧好，但比 `st.status` 更可控），结合颜色状态标记。

**二次决策**：放弃 `st.status`，改为自定义 HTML + CSS 步骤指示器。原因：
- `st.status` 同一位置多次调用会产生重复的 UI 元素
- 自定义 HTML 步骤条更灵活，可以精确控制样式
- 实现成本相近，但效果更好

### 2. 自定义 CSS 注入方式

**方案**：在 `app.py` 开头通过 `st.markdown("<style>...</style>", unsafe_allow_html=True)` 一次性注入所有自定义 CSS。

**替代方案**：外部 CSS 文件 + 读取注入 → 不采用，增加复杂度但无实质收益。

CSS 涵盖：
- 卡片样式（`.card-container`）：白色背景、圆角 12px、阴影、内边距
- 评分颜色（`.score-pass`、`.score-fail`、`.score-warn`）：绿色、红色、橙色
- 步骤指示器（`.stepper`）：水平排列、连接线、状态圆点
- 示例查询芯片（`.query-chip`）：圆角标签、hover 高亮
- 全局间距调整（section 间距、标题大小）

### 3. 信息架构重组：sidebar 分流

当前所有信息在左侧面板垂直堆叠：
```
左侧面板:
  ├── 阶段时间线
  ├── 当前状态
  ├── 研究计划 (expander)
  ├── 检索详情 (expander)
  ├── 质量详情 (expander)
  ├── 重试历史 (expander)
  ├── 耗时统计 (expander)
  ├── 事件日志 (expander)
  └── 进度条
```

重组后：
```
左侧面板 (核心进度):          侧边栏 (辅助信息):
  ├── 步骤指示器              ├── ⏱ 耗时统计
  ├── 当前状态                ├── 📜 事件日志
  ├── 研究计划 (expander)     ├── 🔄 重试历史
  ├── 检索详情 (expander)     └── 📊 实时指标
  ├── 质量详情 (expander)
  └── 进度条
```

这样用户在主区域看到的是"现在在做什么"，在侧边栏看到的是"发生了什么"。

### 4. 空状态引导设计

右侧报告区在 3 种状态下展示不同内容：

| 状态 | 展示内容 |
|------|---------|
| 未开始（`not is_running and not report`） | 功能介绍卡片 + 3 步使用流程 + 示例查询 |
| 运行中（`is_running`） | 流式报告内容（当前行为） |
| 已完成（`not is_running and report`） | 完整报告 + 引用来源（当前行为） |

空状态页面结构：
```
┌─────────────────────────────────────────────┐
│  👋 欢迎使用 Deep Research Agent              │
│                                              │
│  ┌─────┐  ┌─────┐  ┌─────┐                 │
│  │ 1. 输入 │→│ 2. Agent │→│ 3. 获取  │       │
│  │ 研究问题 │  │ 自动研究 │  │ 报告   │       │
│  └─────┘  └─────┘  └─────┘                 │
│                                              │
│  💡 试试这些问题：                            │
│  [AI在医疗影像和药物研发中的应用有什么区别？]    │
│  [Transformer架构相比LSTM有哪些优势？]         │
│  [量子计算对密码学的威胁有多大？]               │
└─────────────────────────────────────────────┘
```

### 5. 示例查询芯片

使用 `st.button` 渲染为小尺寸按钮，排列在输入框下方。点击后将查询文本填入 `st.session_state` 并触发研究。关键实现细节：
- 芯片按钮使用 `type="secondary"` + 小尺寸
- 点击后设置 `st.session_state.query_value` 并触发 `st.rerun()`
- 用 CSS 将按钮样式化为圆角芯片（`border-radius: 20px`）

### 6. Input Form 与 Enter 提交

用 `st.form` 包裹输入区（text_area + submit button），天然支持 Enter 提交。问题在于 `st.form` 外无法触发表单提交，所以芯片点击需要特殊处理：
- 芯片按钮放在 `st.form` 外部
- 点击芯片时设置 session_state 中的 preset_query 变量
- 表单内部 text_area 的 value 绑定到 preset_query

### 7. 真实进度条数据

在 SSE 事件中增加 `progress` 字段（0.0~1.0），后端各阶段完成后上报。前端从事件中读取并设置到 `st.session_state.progress_value`，进度条直接使用该值。

后端改动极轻：在 `backend/services/research_service.py` 发送事件时附带 `progress` 字段：
- plan_start → 0.05 / plan_chunk → 0.10
- retrieval_start → 0.10 + step/total * 0.30 / retrieval_result → 0.10 + step/total * 0.30
- critique_start → 0.40 + step/total * 0.20 / critique_result → 0.40 + step/total * 0.20
- synthesis_start → 0.60 / synthesis_chunk → 0.60~0.90 / done → 1.0

## Risks / Trade-offs

- **Streamlit 的 st.form 与外部的芯片按钮交互复杂** → 芯片点击后不直接提交表单，而是设置预设文本到 text_area，让用户手动提交或再按一次 Enter
- **自定义 CSS 可能与 Streamlit 主题冲突** → 使用足够的特异性选择器，遵循 Streamlit 的 CSS 类名前缀规则
- **sidebar 中渲染动态内容在每次 rerun 时可能闪烁** → 在 sidebar 渲染逻辑中使用 `st.empty()` placeholder 模式
- **进度百分比为估算值** → 在真实系统中各阶段耗时比例可能不准，`done` 事件强制设为 1.0
