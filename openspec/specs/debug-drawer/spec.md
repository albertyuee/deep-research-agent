## ADDED Requirements

### Requirement: Debug drawer is hidden by default with toggle control
系统 SHALL 在页面右上角提供固定位置的齿轮图标（⚙️）按钮，点击后展开/收起调试抽屉。抽屉默认处于隐藏状态。

#### Scenario: Open debug drawer
- **WHEN** 用户点击齿轮图标且抽屉处于关闭状态
- **THEN** 右侧滑出 320px 宽的调试面板，伴随 CSS transition 动画（transform translateX），同时显示半透明遮罩层

#### Scenario: Close debug drawer
- **WHEN** 用户点击抽屉关闭按钮、点击遮罩层、或再次点击齿轮图标
- **THEN** 抽屉滑出屏幕，遮罩层消失，页面恢复正常显示

#### Scenario: Drawer content updates during research
- **WHEN** 研究正在运行且调试抽屉处于打开状态
- **THEN** 抽屉内的事件日志、耗时统计在每次 rerun 时更新为最新数据

### Requirement: Debug drawer displays event log, timing stats, and retry history
调试抽屉 SHALL 包含三个信息模块：事件日志（最后 N 条）、阶段耗时统计、重试历史记录。

#### Scenario: Event log display
- **WHEN** 调试抽屉打开且有事件记录
- **THEN** 显示最近 50 条 SSE 事件的表格（时间戳、事件类型、摘要），按时间倒序排列，可展开查看完整事件数据

#### Scenario: Timing stats display
- **WHEN** 调试抽屉打开且有阶段耗时数据
- **THEN** 显示各阶段的耗时表格（阶段名称、耗时秒数）和累计总时间

#### Scenario: Retry history hidden when no retries
- **WHEN** 研究过程中没有发生重试
- **THEN** 调试抽屉中不显示重试历史模块

### Requirement: Debug drawer does not block main content interaction
调试抽屉 SHALL 以 overlay 方式显示，不挤出或压缩主页面内容。

#### Scenario: Main content remains fully interactive
- **WHEN** 调试抽屉处于打开状态
- **THEN** 主页面内容（报告、进度面板）保持原位不动，抽屉覆盖在其上方，用户仍可滚动和与主内容交互（抽屉外区域）
