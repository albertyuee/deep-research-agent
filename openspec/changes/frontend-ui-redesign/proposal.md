## Why

当前 Streamlit 前端虽然功能完整，但视觉设计和用户体验较为粗糙：阶段时间线用 markdown 删除线/粗体模拟、所有展开面板堆在左侧导致信息过载、右侧报告区在未开始时完全空白、评分缺乏颜色编码、无自定义样式美化。这些问题降低了产品的专业感和用户信心，需要在 MVP 阶段就建立良好的第一印象。

## What Changes

- 右侧面板增加**空状态引导**：首次加载时显示功能介绍、使用流程图、可点击的示例查询，消除空白页面
- 用 `st.status` 原生组件重写**阶段步骤指示器**，替代当前的删除线/粗体 markdown 模拟
- 评分和状态增加**颜色编码**：通过分数显示绿色、失败显示红色、警告显示橙色
- **左侧面板精简**：将事件日志、阶段耗时等辅助信息移至 `st.sidebar`，主面板只保留核心进度
- 添加**自定义 CSS**：卡片容器、圆角、阴影、更好的间距排版
- 输入区增加**示例查询芯片**，点击自动填入输入框
- 进度条改为接入**真实后端进度数据**（后端在 SSE 事件中上报百分比）
- 输入区用 `st.form` 包裹，支持 **Enter 键提交**

## Capabilities

### New Capabilities
- `frontend-empty-state`: 右侧报告区的空状态引导页，包含功能介绍、使用流程说明、可点击的示例查询
- `frontend-theme-styling`: 自定义 CSS 样式系统，包括卡片容器、颜色编码、间距排版、响应式布局
- `frontend-form-input`: 用 st.form 重构输入区，支持 Enter 提交和示例查询快捷填入

### Modified Capabilities
- `frontend-event-log`: 事件日志面板从主进度面板移至 sidebar，保持功能不变但改变展示位置
- `frontend-step-details`: 阶段详细信息（检索详情、质量评估、耗时统计）重新组织，核心进度保留在主面板，辅助信息移至 sidebar

## Impact

- 主要修改：`frontend/app.py`、`frontend/components/agent_progress.py`、`frontend/components/report_view.py`
- 新增文件：`frontend/components/empty_state.py`（空状态组件）、`frontend/static/style.css`（自定义样式）
- 后端需配合：在 SSE 事件中增加 `progress` 字段上报真实进度百分比
- 无新增 Python 依赖，仅使用 Streamlit 内置组件和原生 HTML/CSS
