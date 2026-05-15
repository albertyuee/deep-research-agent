## ADDED Requirements

### Requirement: Idle state shows full-width welcome content
idle 状态下，页面 SHALL 隐藏左侧进度面板，welcome 区域在所有列中占全宽并水平和垂直居中显示。

#### Scenario: First page load
- **WHEN** 用户首次打开页面且未发起过任何研究
- **THEN** 只显示输入区域和全宽居中的 welcome 内容（图标 + 标题 + 副标题 + 3 个步骤卡片 + 示例问题），不显示左侧进度面板，不显示调试面板

#### Scenario: Welcome content is vertically centered
- **WHEN** welcome 内容显示
- **THEN** welcome 容器在可用垂直空间中居中（min-height: 60vh + flexbox justify-content: center），3 个步骤卡片在同一行等宽排列且水平居中

### Requirement: Running state shows progress panel and status bar
研究运行中，页面 SHALL 显示左侧进度面板（1/3 宽）、右侧报告面板（2/3 宽）和顶部状态栏。

#### Scenario: Status bar during running
- **WHEN** 研究处于运行状态
- **THEN** 输入区域下方显示状态栏，包含：当前阶段中文描述、进度条（0-100%）、已用时长（秒）、红色停止按钮

#### Scenario: Status bar progress updates
- **WHEN** 研究过程中收到新的 SSE 事件
- **THEN** 状态栏的进度条根据 `session_state.progress_value` 更新，阶段描述根据 `session_state.current_step` 更新

#### Scenario: Stop button visible only when running
- **WHEN** 研究处于 running 状态
- **THEN** 状态栏中显示可点击的停止按钮；idle / completed / cancelled 状态下不显示停止按钮

### Requirement: Completed state shows full results with progress history
研究正常完成后，页面 SHALL 保留左侧进度面板和右侧报告面板，状态栏显示完成状态信息。

#### Scenario: After normal completion
- **WHEN** 研究正常完成（done 事件）
- **THEN** 报告面板显示完整的结构化报告，来源引用可展开，进度 stepper 所有步骤显示为 complete，输入区域恢复可用

### Requirement: Cancelled state shows cancellation notice with partial results
取消后，页面 SHALL 显示取消提示并保留所有已获取的部分数据，输入区域恢复可用。

#### Scenario: After user cancellation
- **WHEN** 研究被用户取消（cancelled 事件）
- **THEN** 状态栏显示"⚠️ 研究已取消 — 历时 Xs，已保留部分结果"提示，报告面板在已生成文本顶部插入取消提示条，进度 stepper 当前步骤显示为 cancelled 态（红色 ✗），输入区域恢复可用可发起新研究

### Requirement: Input area is compact
输入区域 SHALL 使用紧凑的单行布局，示例问题 chips 在输入框下方内联显示。

#### Scenario: Compact input layout
- **WHEN** 页面处于任何状态
- **THEN** 文本输入框和提交按钮在同一行，示例问题 chips 在输入框下方以 flex wrap 方式排列，整体垂直占用空间不超过 150px
