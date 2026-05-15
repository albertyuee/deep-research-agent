## ADDED Requirements

### Requirement: User can cancel a running research task
系统 SHALL 为用户提供立即终止正在运行的研究任务的能力。取消后已获取的部分报告内容和进度数据 SHALL 保留。

#### Scenario: Cancel during retrieval phase
- **WHEN** 用户在研究运行中点击状态栏上的停止按钮
- **THEN** 后端立即取消 asyncio 任务，SSE 连接关闭，前端显示"研究已取消"提示，已累积的报告文本保留在报告面板中，进度 stepper 显示当前步骤为 cancelled 态

#### Scenario: Cancel during synthesis phase
- **WHEN** 用户在报告合成阶段点击停止按钮
- **THEN** 所有 synthesis_chunk 已累积的文本保留在报告中，进度面板保留所有已完成步骤的数据，状态栏显示取消提示

#### Scenario: Backend not reachable on cancel
- **WHEN** 用户点击停止按钮但后端不可达
- **THEN** 前端断开 SSE 连接并退出运行状态，显示本地取消提示

### Requirement: Backend handles task cancellation
后端 SHALL 通过 `asyncio.Task.cancel()` 支持研究任务的立即取消，并发送 cancelled 事件通知前端。

#### Scenario: Cancel triggers CancelledError in agent
- **WHEN** 后端收到 cancel 请求且 agent 任务正在执行
- **THEN** `asyncio.Task.cancel()` 在下一次 await 时抛出 CancelledError，agent 执行被中断，后端发送 `cancelled` SSE 事件，任务状态变更为 CANCELLED

#### Scenario: Cancel already completed task
- **WHEN** 后端收到 cancel 请求但任务已完成
- **THEN** 返回 409 Conflict，指示任务已不在运行中

### Requirement: Cancel preserves partial results
取消后的状态 SHALL 保留所有已获取的数据，包括部分报告文本、检索结果、评估结果、事件日志和耗时统计。

#### Scenario: Report preserves partial text after cancel
- **WHEN** 研究被取消且已有部分 synthesis_chunk 文本累积
- **THEN** 报告面板显示所有已累积文本，顶部插入取消提示条，进度面板显示已完成步骤的数据

#### Scenario: User can start new research after cancel
- **WHEN** 研究被取消后
- **THEN** 输入区域恢复可用，用户可以立即提交新的研究问题
