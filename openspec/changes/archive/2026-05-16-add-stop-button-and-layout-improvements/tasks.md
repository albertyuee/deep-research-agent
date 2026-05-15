## 1. 后端取消机制

- [x] 1.1 `ResearchTaskManager` 新增 `_running_tasks: dict[str, asyncio.Task]` 存储 agent 任务引用
- [x] 1.2 `TaskStatus` 枚举新增 `CANCELLED = "cancelled"` 状态
- [x] 1.3 `_run_agent()` 中捕获 `asyncio.CancelledError`，发送 `cancelled` SSE 事件，状态更新为 CANCELLED，清理 event_bus
- [x] 1.4 新增 `POST /api/v1/research/{task_id}/cancel` 端点，获取任务引用并调用 `task.cancel()`，已完成的任务返回 409
- [x] 1.5 验证 cancel 信号能穿透 LangGraph `ainvoke`（spike 测试），若不能则在 graph 节点中加入 cancel flag 检查

## 2. 前端异步架构重构

- [x] 2.1 创建 `frontend/thread_worker.py`：worker 线程函数，启动 asyncio event loop 连接后端 SSE，通过 `queue.Queue` 传递事件给主线程
- [x] 2.2 重构 `frontend/app.py` 中的研究执行逻辑：用 `threading.Thread` + `queue.Queue` 替换 `asyncio.run()`
- [x] 2.3 主线程轮询：在每个 Streamlit rerun 周期中消费 queue 中的所有事件，更新 session_state，完成后调用 `st.rerun()`
- [x] 2.4 线程安全：worker 线程只写 queue 不碰 session_state；主线程在 rerun 开始时消费 queue 并更新状态

## 3. 布局状态机

- [x] 3.1 在 `app.py` 中引入 `page_state`（idle / running / completed / cancelled），基于 session_state 推导
- [x] 3.2 idle 态：隐藏左侧进度面板，welcome 区域全宽居中，不显示状态栏
- [x] 3.3 running 态：左栏（1/3）+ 右栏（2/3），显示状态栏（进度条 + 阶段 + 耗时 + 停止按钮），输入区域禁用
- [x] 3.4 completed 态：左栏保留 + 右栏显示完整报告，状态栏显示完成信息，输入区域恢复可用
- [x] 3.5 cancelled 态：左栏保留 + 右栏显示部分报告 + 取消提示条，状态栏显示取消信息，输入区域恢复可用

## 4. 状态栏与停止按钮

- [x] 4.1 在 `app.py` 中实现状态栏组件：显示当前阶段中文描述、进度条（复用 `progress_value`）、已用时长、停止按钮
- [x] 4.2 停止按钮仅在 running 态显示，样式为红色/醒目
- [x] 4.3 停止按钮点击逻辑：设置 `cancel_requested` flag → POST cancel 端点 → worker 线程检测 flag 后清理 → 状态切换为 cancelled

## 5. 调试抽屉

- [x] 5.1 创建 `frontend/components/debug_drawer.py`：渲染事件日志、耗时统计、重试历史
- [x] 5.2 在 `style.css` 中添加抽屉样式：`position: fixed; right: 0; transform: translateX` 滑入/滑出动画，遮罩层
- [x] 5.3 在 `app.py` 中添加齿轮图标按钮和 drawer 状态管理（`session_state.show_debug`）
- [x] 5.4 移除 `app.py` 中所有 `st.sidebar` 用法

## 6. Welcome 居中修复

- [x] 6.1 修改 `empty_state.py`：将所有 welcome 内容（图标、标题、步骤卡片、示例问题）包裹在统一的居中容器 div 中
- [x] 6.2 在 `style.css` 中添加 flexbox 居中样式：`display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 60vh;`

## 7. 输入区域紧凑化

- [x] 7.1 文本输入框和提交按钮改为同行布局（st.columns）
- [x] 7.2 示例问题 chips 在输入框下方内联显示，使用 flex wrap

## 8. 集成验证

- [x] 8.1 端到端测试：正常研究流程（idle → running → completed）
- [x] 8.2 端到端测试：取消流程（idle → running → cancelled → 发起新研究）
- [x] 8.3 验证取消后部分报告文本保留、进度数据保留
- [x] 8.4 验证调试抽屉展开/收起不影响主内容布局
- [x] 8.5 验证 welcome 在各浏览器窗口尺寸下居中显示
