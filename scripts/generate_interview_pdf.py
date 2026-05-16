#!/usr/bin/env python3
"""Generate the Deep Research Agent interview preparation PDF."""

from fpdf import FPDF
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "docs", "Deep_Research_Agent_面试准备.pdf")
OUTPUT_MOBILE = os.path.join(os.path.dirname(__file__), "..", "docs", "Deep_Research_Agent_面试准备_手机版.pdf")
FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"


class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("CN", "", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, "Deep Research Agent — 面试准备", align="R")
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("CN", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"第 {self.page_no()} 页", align="C")

    def title_block(self, text):
        self.set_fill_color(124, 58, 237)
        self.set_text_color(255, 255, 255)
        self.set_font("CN", "", 16)
        self.cell(0, 14, f"  {text}", fill=True, ln=True)
        self.ln(4)

    def h1(self, text):
        self.set_font("CN", "", 14)
        self.set_text_color(124, 58, 237)
        self.cell(0, 10, text, ln=True)
        self.set_draw_color(124, 58, 237)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(4)

    def h2(self, text):
        self.set_font("CN", "", 12)
        self.set_text_color(51, 65, 85)
        self.cell(0, 8, text, ln=True)
        self.ln(2)

    def h3(self, text):
        self.set_font("CN", "", 10.5)
        self.set_text_color(71, 85, 105)
        self.cell(0, 7, text, ln=True)
        self.ln(1)

    def body(self, text):
        self.set_font("CN", "", 9.5)
        self.set_text_color(55, 65, 81)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text, indent=8):
        self.set_font("CN", "", 9.5)
        self.set_text_color(55, 65, 81)
        x = self.get_x()
        self.cell(indent, 5.5, "")
        self.set_font("CN", "", 9.5)
        bullet_char = "•"
        self.cell(5, 5.5, bullet_char)
        self.multi_cell(0, 5.5, text)

    def code_block(self, text):
        self.set_fill_color(31, 41, 55)
        self.set_text_color(229, 231, 235)
        self.set_font("CN", "", 8)
        lines = text.strip().split("\n")
        self.ln(2)
        for line in lines:
            self.cell(10, 4.5, "")  # indent
            self.cell(0, 4.5, line, ln=True)
        self.set_text_color(55, 65, 81)
        self.ln(3)

    def table_row(self, cells, widths, header=False):
        if header:
            self.set_fill_color(124, 58, 237)
            self.set_text_color(255, 255, 255)
            self.set_font("CN", "", 9)
        else:
            self.set_fill_color(248, 250, 252)
            self.set_text_color(55, 65, 81)
            self.set_font("CN", "", 8.5)
        row_h = 7
        for i, (cell, w) in enumerate(zip(cells, widths)):
            if i == 0:
                self.cell(4, row_h, "")
            self.cell(w, row_h, cell, border=0, fill=True)
        self.ln(row_h)

    def highlight_box(self, text):
        self.set_fill_color(245, 243, 255)
        self.set_text_color(124, 58, 237)
        self.set_font("CN", "", 9)
        self.set_x(self.get_x() + 6)
        self.multi_cell(180, 5.5, text, fill=True)
        self.ln(3)

    def check_page_break(self, h=30):
        if self.get_y() > 270 - h:
            self.add_page()


def build():
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_font("CN", "", FONT_PATH)
    pdf.add_page()

    # ── Cover ──
    pdf.ln(30)
    pdf.set_font("CN", "", 28)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 16, "Deep Research Agent", align="C", ln=True)
    pdf.set_font("CN", "", 14)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 10, "Agentic RAG 自主深度研究系统", align="C", ln=True)
    pdf.ln(8)
    pdf.set_draw_color(124, 58, 237)
    pdf.set_line_width(0.5)
    pdf.line(50, pdf.get_y(), 160, pdf.get_y())
    pdf.ln(12)
    pdf.set_font("CN", "", 11)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 8, "Agent 开发工程师面试准备材料", align="C", ln=True)
    pdf.ln(20)
    pdf.set_font("CN", "", 9.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 7, "技术栈: LangGraph + FastAPI + Vue 3 + ChromaDB + BM25 + SSE", align="C", ln=True)
    pdf.cell(0, 7, "源代码: github.com/956501819/deep-research-agent", align="C", ln=True)
    pdf.cell(0, 7, "生成日期: 2026-05-16", align="C", ln=True)

    # ── Page 2: Overview ──
    pdf.add_page()
    pdf.h1("一、项目概述")
    pdf.body(
        "Deep Research Agent 是一个基于 Agentic RAG 的自主深度研究系统。与传统 RAG 不同，"
        "它不是一个简单的「检索-回答」流程——Agent 会主动拆解复杂问题、自主选择最优检索策略、"
        "评估检索结果质量、在质量不达标时自我纠正并重试，最终生成带有内联引用和溯源的结构化研究报告。"
    )
    pdf.body(
        "项目完整覆盖了 AI Agent 开发的核心技术栈："
        "LangGraph 编排引擎、多 Provider LLM 封装、混合检索（向量+BM25+RRF融合）、"
        "检索质量 Critique、查询改写与重试控制、SSE 流式推送、以及 Vue 3 工程化前端。"
    )

    pdf.h2("核心数据")
    pdf.body(f"• Agent 核心模块: 27 个 Python 文件（planner / retrieval / critique / synthesis）")
    pdf.body(f"• 后端 API: 4 个路由模块（research / quick-search / documents / settings），15+ 端点")
    pdf.body(f"• 前端: 34 个 Vue 3 / TypeScript 文件，4 个完整功能页面")
    pdf.body(f"• 提交记录: 47 次渐进式 commit，从 MVP 到完整工程化落地")

    pdf.h2("与传统 RAG 的关键区别")

    widths = [64, 64, 64]
    pdf.table_row(["维度", "传统 RAG", "Deep Research Agent"], widths, header=True)
    pdf.table_row(["检索次数", "1 次", "最多 3 次（自适应重试）"], widths)
    pdf.table_row(["检索策略", "固定向量检索", "Agent 自主选择 semantic/keyword/hybrid"], widths)
    pdf.table_row(["质量判断", "无", "LLM 双维度评分（相关性+完整性）"], widths)
    pdf.table_row(["查询改写", "无", "3 级升级（broaden → switch → rephrase）"], widths)
    pdf.table_row(["输出", "单次回答", "结构化报告 + 内联引用 + 溯源"], widths)
    pdf.table_row(["Agent 框架", "无 / 黑盒", "LangGraph StateGraph 显式状态机"], widths)
    pdf.ln(6)

    # ── Tech Stack ──
    pdf.h1("二、技术栈全景")
    pdf.body("以下按架构分层列出项目使用的所有核心技术，以及每项技术在面试中可以展开讨论的要点。")

    widths2 = [36, 56, 100]
    pdf.table_row(["层级", "技术选型", "面试讨论要点"], widths2, header=True)
    pdf.table_row(["Agent 编排", "LangGraph StateGraph", "显式状态流转+条件路由，非黑盒AgentExecutor"], widths2)
    pdf.table_row(["LLM 接入", "SiliconFlow / Qwen / OpenAI", "Factory 模式统一封装，多Provider无感切换"], widths2)
    pdf.table_row(["向量存储", "ChromaDB (Persistent)", "嵌入式部署，余弦相似度，可切换 Milvus"], widths2)
    pdf.table_row(["关键词检索", "BM25 (rank-bm25)", "互补语义检索，中文分词适配"], widths2)
    pdf.table_row(["混合检索", "RRF (k=60)", "稠密向量 + 稀疏BM25 融合重排序"], widths2)
    pdf.table_row(["Embedding", "BGE-large-zh-v1.5", "1024维，本地/API双模式，批量优化"], widths2)
    pdf.table_row(["后端框架", "FastAPI + SSE", "异步+流式，12+ REST端点，CORS中间件"], widths2)
    pdf.table_row(["前端框架", "Vue 3 + Vite + TypeScript", "Composition API, Pinia, Naive UI, Tailwind"], widths2)
    pdf.table_row(["状态管理", "Pinia (research/chat/documents/settings)", "4个Store，替代Streamlit session_state"], widths2)
    pdf.table_row(["SSE 客户端", "原生 EventSource", "无额外依赖，自动重连，事件分发到Pinia"], widths2)
    pdf.table_row(["文档处理", "PyMuPDF + python-docx", "PDF/Word/MD/TXT 四格式支持"], widths2)
    pdf.table_row(["配置管理", "pydantic-settings + .env", "类型安全+环境变量+热重载"], widths2)
    pdf.ln(6)

    # ── Architecture ──
    pdf.check_page_break(80)
    pdf.h1("三、Agent 架构详解")
    pdf.h2("3.1 LangGraph 状态流转")
    pdf.body(
        "Agent 使用 LangGraph StateGraph 显式定义了 4 个节点和 1 个条件路由。"
        "与 LangChain 的 AgentExecutor（黑盒）不同，每一步的状态变化都是显式的、可观测的。"
    )

    pdf.code_block("""用户问题
  → Decomposition Node: LLM 拆解为 2-5 个子问题，每个标注检索策略
  → Retrieval Node: 策略路由（semantic / keyword / hybrid）+ 查询改写
  → Critique Node: 双维度评分（相关性 + 完整性），决定 pass/fail
  → Conditional Edge (should_retry):
      [PASS] pass → next step or Synthesis
      [FAIL] fail + can retry → back to Retrieval (改写查询、切换策略)
      [FAIL] fail + exhausted → 标记低置信度，继续下一步
  → Synthesis Node: 多源聚合 + 冲突检测 + LLM 生成 + 引用标注""")

    pdf.h2("3.2 四个节点的职责")
    pdf.h3("Decomposition Node（拆解）")
    pdf.body(
        "LLM 将用户问题拆解为 2-5 个子问题，每个子问题标注最优检索策略（semantic / keyword / hybrid），"
        "给出策略选择理由（rationale）。同时初始化整个研究状态：total_steps、current_step、retry_count 等。"
        "SSE 事件: research_plan_start → research_plan_chunk × N"
    )

    pdf.h3("Retrieval Node（检索）")
    pdf.body(
        "根据当前子问题的策略标签路由到不同的检索方法：semantic 走纯向量检索、keyword 走纯 BM25、"
        "hybrid 走两者 RRF 融合。如果是重试，还会调用 QueryRewriter 改写查询——第1次 broaden（扩展）、"
        "第2次 switch（切换策略）、第3次 rephrase（改写表达）。top_k 随重试次数指数扩展。"
        "SSE 事件: retrieval_start → retrieval_result"
    )

    pdf.h3("Critique Node（评估）")
    pdf.body(
        "LLM 对当前检索结果进行双维度评分：相关性（relevance，0-1）和完整性（completeness，0-1），"
        "综合得到 composite_score。评分 ≥ critique_threshold（默认 0.6）即为通过。"
        "不通过时给出 retry_suggestion，指导下一次重试的改写方向。"
        "SSE 事件: critique_start → critique_result { composite_score, relevance, completeness, passed, retry_suggestion }"
    )

    pdf.h3("Synthesis Node（合成）")
    pdf.body(
        "所有子问题检索完成后进入合成阶段。先通过 Aggregator 对多源结果去重聚合 + 冲突检测，"
        "再通过 ReportGenerator 流式生成结构化 Markdown 报告。最后通过 CitationBuilder "
        "为每条引用生成编号标注 [1] [2]... 并在文末附加参考资料列表。"
        "SSE 事件: synthesis_start → synthesis_chunk × N → done"
    )

    pdf.h2("3.3 自我纠错机制")
    pdf.body(
        "这是本系统与普通 RAG 最核心的区别。当一次检索结果被评为不合格时，Agent 不会简单地接受"
        "低质量结果，而是启动一个 3 级逐步升级的重试策略："
    )
    pdf.body("• 第 1 次重试 (broaden): 扩展查询范围，增加同义词和相关概念")
    pdf.body("• 第 2 次重试 (switch): 切换检索策略（语义↔关键词），同时 top_k × 2")
    pdf.body("• 第 3 次重试 (rephrase): 完全改写查询表达方式，top_k × 4")
    pdf.body(
        '3 次重试后若仍不达标，Agent 将当前步骤标记为 low_confidence，使用「最佳可用结果」继续，'
        '并在最终报告中标注该部分可信度较低。这种机制保证了系统不会在单点卡死，同时保持信息透明度。'
    )

    # ── Key Highlights ──
    pdf.check_page_break(60)
    pdf.h1("四、项目亮点与面试高频问题")

    qa = [
        ("为什么用 LangGraph 而不是 LangChain AgentExecutor？",
         "LangChain 的 AgentExecutor 是黑盒——你无法精确控制 Agent 在每个步骤做什么决策、"
         "如何选择工具、何时停止。LangGraph StateGraph 让我显式定义了 4 个节点 + 1 个条件路由，"
         "每一步的状态变化完全可控、可观测、可调试。这在生产环境中至关重要——当 Agent 做了错误决策时，"
         "你可以精确追溯到哪个节点、什么状态下出了问题。"),
        ("为什么 Critique 是独立节点而不是放在 Retrieval 里面？",
         "职责分离（Separation of Concerns）。Critique 可以用 LLM 评分（当前实现），"
         "也可以替换为 Cross-Encoder 重排序模型、规则引擎、甚至人工审核——"
         "改 Critique 不影响 Retrieval，改 Retrieval 不影响 Critique。"
         "这是 Agent 架构设计的基本功：每个节点只做一件事，接口清晰，可插拔。"),
        ("混合检索 vs 纯向量检索，为什么需要 BM25？",
         "向量检索擅长语义匹配但对于精确匹配（数字、专有名词、代码、公式）效果差。"
         "例如查询 'BERT-base 参数量 110M'，向量可能返回关于 BERT 架构的长篇描述，"
         "但 BM25 能精确命中包含 '110M' 的句子。RRF（Reciprocal Rank Fusion）"
         "将两者的排名融合，k=60 是实验验证的较优参数。"),
        ("如何控制 Agent 的幻觉？",
         "三层控制：(1) Critique 阈值过滤——检索质量 < 0.6 触发重试而非强行回答；"
         "(2) System Prompt 约束——明确要求「检索不到就如实告知」；"
         "(3) 低置信度标记——重试耗尽后在报告中显式标注该部分的可靠性存疑。"),
        ("SSE vs WebSocket 为什么选 SSE？",
         "单向推送够用——后端推送事件、前端接收展示，不需要双向通信。"
         "SSE 协议更轻量，浏览器原生 EventSource API 自带自动重连，不需要额外的 WebSocket 库。"
         "我们的 SSE 事件粒度细化到每个子步骤（plan_chunk、retrieval_result、critique_result），"
         "让用户实时感知 Agent 在想什么——这是 UX 的关键。"),
        ("前端为什么从 Streamlit 迁移到 Vue 3？",
         "Streamlit 开发快但局限大：(1) session_state + queue.Queue + st.rerun() 轮询模式脆弱，"
         "DOM 残留问题频发；(2) 自定义样式只能通过 unsafe_allow_html 注入 CSS；"
         "(3) 无法实现多页面路由、侧边栏导航、对话 UI 等复杂交互。"
         "Vue 3 的响应式系统天然解决状态同步，EventSource 替代轮询，Pinia 替代 session_state，"
         "组件化开发让每个功能模块独立可测试。"),
        (".env 热重载如何实现？",
         "PATCH /api/v1/settings → 逐行读写 .env 文件（不用 dotenv_values 解析——对特殊字符太脆弱）"
         "→ 正则匹配 KEY=VALUE → 替换或追加 → 重建 Settings 单例 → 下次 LLM/Embedding 调用即生效。"
         "API Key 字段被掩码处理（sk-***buji），掩码值不会写回 .env。"),
        ("如何测试 Agent 行为？",
         "26 个 pytest 单元测试覆盖核心逻辑（decomposition / retrieval / critique / graph 流转）。"
         "Agent 运行时的每一步行为通过 SSE 事件日志完整记录——包括事件类型、时间戳、数据 payload，"
         "在生产环境中这就是天然的 audit log。"),
    ]

    for q, a in qa:
        pdf.check_page_break(35)
        pdf.h3(f"Q: {q}")
        pdf.body(f"A: {a}")
        pdf.ln(2)

    # ── Frontend ──
    pdf.check_page_break(40)
    pdf.h1("五、前端工程化")
    pdf.body(
        "前端从 Streamlit 完全迁移至 Vue 3 + Vite + TypeScript，4 个功能页面，34 个源文件。"
    )

    widths3 = [40, 48, 104]
    pdf.table_row(["页面", "路由", "功能"], widths3, header=True)
    pdf.table_row(["深度研究", "/", "Agent 进度实时可视化 + Markdown 报告流式渲染 + 来源引用"], widths3)
    pdf.table_row(["快速检索", "/quick-search", "对话式 UI，即时问答，秒级响应"], widths3)
    pdf.table_row(["资料管理", "/documents", "上传/预览/删除，自动分块+嵌入+索引"], widths3)
    pdf.table_row(["系统设置", "/settings", "LLM/嵌入/检索配置，热重载生效"], widths3)
    pdf.ln(4)

    pdf.body("技术架构：Vue Router (4 路由) + Pinia (4 Store) + 原生 EventSource (SSE) + Naive UI + Tailwind CSS")
    pdf.body("状态管理对比 Streamlit 改进：st.session_state → Pinia Store / queue.Queue → EventSource / st.rerun() 轮询 → Vue 响应式系统")

    # ── API ──
    pdf.check_page_break(40)
    pdf.h1("六、后端 API 设计")
    widths4 = [28, 52, 112]
    pdf.table_row(["方法", "端点", "说明"], widths4, header=True)
    pdf.table_row(["POST", "/api/v1/research", "提交深度研究任务，返回 task_id"], widths4)
    pdf.table_row(["GET", "/api/v1/research/{id}/stream", "SSE 流，推送 Agent 全生命周期事件"], widths4)
    pdf.table_row(["GET", "/api/v1/research/{id}", "查询任务状态和最终结果"], widths4)
    pdf.table_row(["POST", "/api/v1/research/{id}/cancel", "取消运行中的任务"], widths4)
    pdf.table_row(["POST", "/api/v1/quick-search", "快速检索 + AI 摘要，同步返回，秒级响应"], widths4)
    pdf.table_row(["GET", "/api/v1/documents", "文件列表（含 ChromaDB 已索引文档）"], widths4)
    pdf.table_row(["POST", "/api/v1/documents/upload", "上传文档 (multipart), 自动分块+嵌入+索引"], widths4)
    pdf.table_row(["DELETE", "/api/v1/documents/{id}", "删除文档及所有关联 chunks"], widths4)
    pdf.table_row(["GET", "/api/v1/settings", "读取当前配置 (API Key 掩码)"], widths4)
    pdf.table_row(["PATCH", "/api/v1/settings", "部分更新配置，写 .env + 热重载"], widths4)
    pdf.table_row(["GET", "/api/v1/settings/system-info", "ChromaDB 统计 + 版本信息"], widths4)
    pdf.ln(6)

    # ── SSE Events ──
    pdf.h2("SSE 事件流")
    widths5 = [46, 50, 96]
    pdf.table_row(["事件", "数据", "触发时机"], widths5, header=True)
    pdf.table_row(["research_plan_start", "{query}", "开始拆解"], widths5)
    pdf.table_row(["research_plan_chunk", "{index, question, strategy, rationale}", "每个子问题"], widths5)
    pdf.table_row(["retrieval_start", "{step, total, strategy, retry_count}", "开始检索"], widths5)
    pdf.table_row(["retrieval_result", "{result_count, top_score, top_preview}", "检索完成"], widths5)
    pdf.table_row(["critique_start", "{step}", "开始评估"], widths5)
    pdf.table_row(["critique_result", "{composite_score, relevance, completeness, passed}", "评估完成"], widths5)
    pdf.table_row(["retry_triggered", "{step, count}", "触发重试"], widths5)
    pdf.table_row(["synthesis_start", "{total_steps}", "开始合成"], widths5)
    pdf.table_row(["synthesis_chunk", "{text}", "报告流式片段"], widths5)
    pdf.table_row(["done", "{report_length}", "全部完成"], widths5)
    pdf.ln(6)

    # ── Demo Flow ──
    pdf.check_page_break(40)
    pdf.h1("七、演示流程建议")
    pdf.body("面试演示控制在 5-8 分钟，按照以下顺序逐步展示系统的核心能力：")
    steps = [
        ("1. 空状态展示 (30s)", "展示欢迎页和三个步骤引导，介绍整体功能布局"),
        ("2. 深度研究 (3min)", '输入「Transformer相比LSTM有哪些优势？」→ 观察Stepper四个阶段 → 左侧面板展示拆解的子问题和检索评分 → 右侧报告流式生成 → 来源引用卡片'),
        ("3. 快速检索 (1min)", "切换到侧边栏「快速检索」→ 输入问题 → 秒级回复 + AI摘要 + 来源折叠"),
        ("4. 资料管理 (1min)", "侧边栏「资料管理」→ 上传一个PDF → 自动分块索引 → 卡片出现 → 预览和删除功能"),
        ("5. 系统设置 (30s)", "侧边栏「系统设置」→ 展示 LLM/嵌入/检索配置 → 说明热重载机制"),
    ]
    for title, desc in steps:
        pdf.h3(title)
        pdf.body(desc)

    # ── Self-Intro ──
    pdf.check_page_break(50)
    pdf.h1("八、自我介绍模板")
    pdf.body("以下是 2-3 分钟的面试自我介绍，可根据实际情况调整：")
    pdf.ln(2)
    pdf.highlight_box(
        "我开发了一个基于 Agentic RAG 的深度研究 Agent，核心价值是让 Agent 具备主动研究能力，"
        "而不是被动回答。技术上用 LangGraph StateGraph 做显式状态编排——定义了拆解、检索、评估、"
        "合成四个节点和一个条件路由——每一步状态都可观测可调试。检索层是混合检索，向量+BM25+RRF融合，"
        "Agent 会根据问题特征自主选择检索策略。最核心的是自我纠错机制——检索质量不达标时，"
        "Agent 自动改写查询、切换策略，最多3次逐步升级重试。后端 FastAPI + SSE 流式推送，"
        "前端 Vue 3 + TypeScript 做了完整的工程化落地——四个功能模块、34个前端文件、"
        "12+ REST端点。整个项目47次渐进式提交，从设计文档到代码都有完整记录。"
    )
    pdf.ln(8)

    # ── Extra Deep Questions ──
    pdf.h1("九、深度追问预案")
    deep_qa = [
        ("为什么不直接用 LangChain 的 create_retrieval_chain？",
         "那是单次检索+回答模式。我的场景是复杂研究问题需要多步推理——拆解成子问题、"
         "每个子问题独立检索和评估、失败后重试。create_retrieval_chain 做不到这个闭环。"),
        ("ChromaDB 如果数据量大了怎么办？",
         "ChromaDB 适合中小规模（10万级chunks）。更大的场景可以替换为 Milvus——"
         "我的 VectorStore 是抽象接口，切换只需改一个类。配置里已经预留了 MILVUS_ 前缀。"),
        ("多轮对话怎么设计？",
         "当前每个研究任务独立。扩展方案：在 Pinia chat store 中维护对话历史，"
         "作为 research 请求的 context 参数传入后端。SSE 事件流天然支持追加。"),
        ("RAGAS 评估怎么集成？",
         "Critique Node 目前用 LLM 评分。可以并行接入 RAGAS 指标（faithfulness、"
         "answer_relevancy、context_precision）作为客观评估维度，与 LLM 主观评分互补。"),
        ("如果 LLM 挂了怎么处理？",
         "所有 LLM 调用都有 exception 捕获+SSE error 事件。前端显示明确的错误提示。"
         "多 Provider 架构（Factory 模式）可以通过配置快速切换备用 Provider。"),
    ]
    for q, a in deep_qa:
        pdf.check_page_break(25)
        pdf.h3(f"Q: {q}")
        pdf.body(f"A: {a}")
        pdf.ln(1)

    pdf.ln(6)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)
    pdf.set_font("CN", "", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, "Deep Research Agent — Agent 开发工程师面试准备材料", align="C", ln=True)
    pdf.cell(0, 6, "技术栈: LangGraph + FastAPI + Vue 3 + ChromaDB + BM25 + SSE", align="C", ln=True)

    # ── Save ──
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    pdf.output(OUTPUT)
    print(f"PDF generated: {OUTPUT}")
    print(f"Pages: {pdf.page_no()}")


# ═══════════════════════════════════════════════════════════════
# Mobile-optimized version (smaller page, larger fonts)
# ═══════════════════════════════════════════════════════════════

class MobilePDF(FPDF):
    """Phone-screen-friendly PDF: narrow width, large fonts, single column."""

    def __init__(self):
        super().__init__('P', 'mm', (120, 200))  # Phone-like proportions
        self.set_auto_page_break(auto=True, margin=10)
        self.add_font("CN", "", FONT_PATH)
        self.set_margin(8)

    def footer(self):
        self.set_y(-10)
        self.set_font("CN", "", 7)
        self.set_text_color(180, 180, 180)
        self.cell(0, 6, f"- {self.page_no()} -", align="C")

    def title_block(self, text):
        self.set_fill_color(124, 58, 237)
        self.set_text_color(255, 255, 255)
        self.set_font("CN", "", 14)
        self.ln(2)
        self.cell(0, 10, f"  {text}", fill=True, ln=True)
        self.ln(3)

    def h1(self, text):
        self.set_x(self.l_margin)
        self.ln(2)
        self.set_font("CN", "", 13)
        self.set_text_color(124, 58, 237)
        self.cell(self.w - self.l_margin - self.r_margin, 8, text, ln=True)
        self.set_draw_color(200, 200, 200)
        self.line(self.get_x(), self.get_y(), self.get_x() + 104, self.get_y())
        self.ln(3)

    def h2(self, text):
        self.set_x(self.l_margin)
        self.set_font("CN", "", 11)
        self.set_text_color(51, 65, 85)
        self.cell(self.w - self.l_margin - self.r_margin, 7, text, ln=True)
        self.ln(1)

    def body(self, text):
        self.set_x(self.l_margin)
        self.set_font("CN", "", 9.5)
        self.set_text_color(55, 65, 81)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 6, text)
        self.ln(1)

    def bullet(self, text):
        self.set_font("CN", "", 9.5)
        self.set_text_color(55, 65, 81)
        self.set_x(self.l_margin)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 6, f"  • {text}")
        self.set_x(self.l_margin)

    def code_block(self, text):
        self.set_fill_color(31, 41, 55)
        self.set_text_color(229, 231, 235)
        self.set_font("CN", "", 8)
        self.ln(1)
        for line in text.strip().split("\n"):
            self.cell(4, 4, "")
            self.cell(0, 4, line, ln=True)
        self.set_text_color(55, 65, 81)
        self.ln(2)

    def highlight_box(self, text):
        self.set_x(self.l_margin)
        self.set_fill_color(245, 243, 255)
        self.set_text_color(124, 58, 237)
        self.set_font("CN", "", 9)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 6, text, fill=True)
        self.ln(2)

    def table_simple(self, rows, col_widths):
        """Simple table without header styling (mobile-friendly)."""
        for i, (cells, is_header) in enumerate(rows):
            if is_header:
                self.set_fill_color(124, 58, 237)
                self.set_text_color(255, 255, 255)
                self.set_font("CN", "", 8.5)
            else:
                self.set_fill_color(248, 250, 252) if i % 2 == 0 else self.set_fill_color(255, 255, 255)
                self.set_text_color(55, 65, 81)
                self.set_font("CN", "", 8)
            for cell, w in zip(cells, col_widths):
                self.cell(w, 5.5, cell, border=0, fill=True)
            self.ln(5.5)

    def separator(self):
        self.ln(3)
        self.set_draw_color(220, 220, 220)
        self.line(8, self.get_y(), 112, self.get_y())
        self.ln(3)

    def qa_item(self, q, a):
        """Render a Q&A in a mobile-friendly format."""
        self.set_x(self.l_margin)
        self.set_font("CN", "", 10)
        self.set_text_color(124, 58, 237)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 7, f"Q: {q}")
        self.ln(1)
        self.set_font("CN", "", 9)
        self.set_text_color(55, 65, 81)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 6, a)
        self.ln(3)


def build_mobile():
    pdf = MobilePDF()
    pdf.add_page()

    # ── Cover ──
    pdf.ln(20)
    pdf.set_font("CN", "", 20)
    pdf.set_text_color(124, 58, 237)
    pdf.multi_cell(0, 12, "Deep Research\nAgent", align="C")
    pdf.ln(2)
    pdf.set_font("CN", "", 11)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, "Agentic RAG 自主深度研究", align="C", ln=True)
    pdf.ln(4)
    pdf.line(30, pdf.get_y(), 90, pdf.get_y())
    pdf.ln(8)
    pdf.set_font("CN", "", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 7, "Agent 开发工程师面试准备", align="C", ln=True)
    pdf.ln(12)
    pdf.set_font("CN", "", 8.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, "LangGraph + FastAPI + Vue 3", align="C", ln=True)
    pdf.cell(0, 6, "+ ChromaDB + BM25 + SSE", align="C", ln=True)
    pdf.ln(6)
    pdf.cell(0, 6, "2026-05-16", align="C", ln=True)

    # ── Overview ──
    pdf.add_page()
    pdf.h1("一、项目概述")
    pdf.body(
        "基于 Agentic RAG 的自主深度研究系统。Agent 会主动拆解复杂问题、自主选择检索策略、"
        "评估结果质量、在质量不达标时自我纠错，最终生成带引用的结构化研究报告。"
    )
    pdf.body("完整覆盖 AI Agent 核心技术栈：LangGraph 编排、多 Provider LLM、混合检索、检索质量 Critique、查询改写重试、SSE 流式推送、Vue 3 前端。")
    pdf.separator()

    pdf.h2("与传统 RAG 的关键区别")
    pdf.table_simple([
        (["维度", "传统 RAG", "本系统"], True),
        (["检索次数", "1次", "最多3次（自适应重试）"], False),
        (["检索策略", "固定向量", "Agent自主选择策略"], False),
        (["质量判断", "无", "双维度LLM评分"], False),
        (["查询改写", "无", "3级升级策略"], False),
        (["输出", "单次回答", "结构化报告+引用"], False),
    ], [22, 36, 46])

    # ── Tech Stack ──
    pdf.separator()
    pdf.h1("二、技术栈全景")
    pdf.body("以下按架构分层列出项目使用的核心技术，以及每项技术在面试中的讨论要点：")
    pdf.table_simple([
        (["层级", "技术", "面试要点"], True),
        (["Agent编排", "LangGraph", "显式状态机，非黑盒Agent"], False),
        (["LLM", "SiliconFlow/Qwen/OpenAI", "Factory模式多Provider"], False),
        (["向量库", "ChromaDB", "持久化+余弦相似度"], False),
        (["关键词", "BM25(rank-bm25)", "互补语义检索"], False),
        (["混合检索", "RRF融合(k=60)", "向量+BM25重排序"], False),
        (["Embed", "BGE-large-zh-v1.5", "1024维，本地/API双模式"], False),
        (["后端", "FastAPI+SSE", "异步流式，12+端点"], False),
        (["前端", "Vue3+Vite+TS", "CompositionAPI+Pinia"], False),
        (["组件库", "Naive UI+Tailwind", "4页面34源文件"], False),
        (["文档", "PyMuPDF+docx", "PDF/Word/MD/TXT"], False),
        (["配置", "pydantic-settings", "类型安全+热重载"], False),
    ], [22, 36, 46])

    # ── Architecture ──
    pdf.add_page()
    pdf.h1("三、Agent 架构详解")
    pdf.h2("LangGraph 状态流转")
    pdf.code_block("""用户问题
 → Decomposition: LLM拆解2-5个子问题
 → Retrieval: 策略路由+查询改写
 → Critique: 双维度评分(pass/fail)
 → 条件路由:
   [PASS] → next or Synthesis
   [FAIL]+can retry → 改写重试
   [FAIL]+exhausted → 标记低置信度
 → Synthesis: 聚合+报告+引用""")

    pdf.h2("四个节点职责")
    pdf.body("Decomposition: LLM拆解问题为2-5个子问题，每个标注最优检索策略（semantic/keyword/hybrid），给出选择理由。")
    pdf.body("Retrieval: 按策略标签路由检索方法。重试时调用QueryRewriter改写查询——L1 broaden（扩展）、L2 switch（切换策略）、L3 rephrase（改写表达），top_k随重试指数扩展。")
    pdf.body("Critique: LLM双维度评分——相关性(relevance)+完整性(completeness)→composite_score。≥0.6通过，否则给出retry_suggestion。")
    pdf.body("Synthesis: Aggregator去重聚合+冲突检测→ReportGenerator流式生成Markdown→CitationBuilder内联引用标注。")

    pdf.h2("自我纠错机制（核心亮点）")
    pdf.body("这是与传统RAG最核心的区别。检索不合格时Agent不会接受低质量结果，而是启动3级升级重试：")
    pdf.bullet("L1 broaden: 扩展查询范围，增加同义词")
    pdf.bullet("L2 switch: 切换检索策略，top_k × 2")
    pdf.bullet("L3 rephrase: 完全改写表达，top_k × 4")
    pdf.body("3次后仍不达标→标记low_confidence→用最佳可用结果继续→报告中标注可信度较低。保证不卡死+信息透明。")

    # ── Key Highlights ──
    pdf.add_page()
    pdf.h1("四、核心面试问答")

    qa_mobile = [
        ("为什么用LangGraph而不是LangChain AgentExecutor？",
         "LangChain AgentExecutor是黑盒——无法精确控制每一步。LangGraph StateGraph显式定义4个节点+1个条件路由，每一步状态完全可控、可观测、可调试。生产环境中当Agent做错误决策时，可以精确追溯到哪个节点、什么状态下出了问题。"),
        ("为什么Critique是独立节点？",
         "职责分离。Critique可以用LLM评分（当前）、Cross-Encoder重排序、规则引擎、甚至人工审核——改Critique不影响Retrieval，改Retrieval不影响Critique。每个节点只做一件事，接口清晰，可插拔。"),
        ("混合检索vs纯向量检索？",
         "向量检索擅长语义匹配但精确匹配差（数字、专有名词）。BM25互补。例如查询'BERT-base参数量110M'，向量可能返回BERT架构长篇描述，但BM25能精确命中'110M'。RRF融合两者排序，k=60是实验验证的较优参数。"),
        ("如何控制Agent幻觉？",
         "三层控制：(1)Critique阈值过滤——质量<0.6触发重试而非强行回答；(2)System Prompt约束'检索不到就说不确定'；(3)低置信度标记——重试耗尽后在报告中标注可靠性存疑。"),
        ("SSEvsWebSocket为什么选SSE？",
         "单向推送够用，不需要双向通信。SSE更轻量，浏览器原生EventSource自带自动重连。事件粒度细化到每个子步骤，让用户实时感知Agent思考过程。"),
        ("前端为什么从Streamlit迁移到Vue3？",
         "Streamlit的session_state+queue.Queue+st.rerun()轮询模式脆弱，DOM残留频发。Vue3响应式系统天然解决状态同步，EventSource替代轮询，Pinia替代session_state，组件化让每个模块独立可测试。"),
        (".env热重载怎么实现？",
         "PATCH→逐行读写.env（不用dotenv_values解析，对特殊字符太脆弱）→正则匹配KEY=VALUE→替换/追加→重建Settings单例→下次LLM调用即生效。API Key掩码后不会回写。"),
    ]

    for q, a in qa_mobile:
        pdf.qa_item(q, a)
        pdf.separator()

    # ── Frontend & API ──
    pdf.add_page()
    pdf.h1("五、前端工程化")
    pdf.body("Vue 3 + Vite + TypeScript + Naive UI + Tailwind CSS，4个功能页面，34个源文件。")
    pdf.table_simple([
        (["页面", "路由", "功能"], True),
        (["深度研究", "/", "Agent进度可视化+报告流式渲染"], False),
        (["快速检索", "/quick-search", "对话式UI，秒级响应"], False),
        (["资料管理", "/documents", "上传/预览/删除，自动索引"], False),
        (["系统设置", "/settings", "LLM/嵌入/检索配置，热重载"], False),
    ], [24, 30, 50])

    pdf.separator()
    pdf.h1("六、后端API设计")
    pdf.table_simple([
        (["方法", "端点", "说明"], True),
        (["POST", "/api/v1/research", "提交深度研究"], False),
        (["GET", "/.../{id}/stream", "SSE流式推送"], False),
        (["POST", "/.../quick-search", "快速检索+AI摘要"], False),
        (["GET/POST/DEL", "/.../documents", "资料管理CRUD"], False),
        (["GET/PATCH", "/.../settings", "配置读/写+热重载"], False),
    ], [28, 38, 38])

    pdf.separator()
    pdf.h2("SSE事件流")
    pdf.table_simple([
        (["事件", "数据", "时机"], True),
        (["plan_start", "{query}", "开始拆解"], False),
        (["plan_chunk", "{index,question,strategy}", "每个子问题"], False),
        (["retrieval_start", "{step,total,strategy}", "开始检索"], False),
        (["retrieval_result", "{count,top_score}", "检索完成"], False),
        (["critique_result", "{score,relevance,passed}", "评估完成"], False),
        (["synthesis_chunk", "{text}", "报告流式片段"], False),
        (["done", "{report_length}", "全部完成"], False),
    ], [32, 40, 32])

    # ── Demo Flow ──
    pdf.add_page()
    pdf.h1("七、演示流程（5-8分钟）")
    steps_mobile = [
        ("1. 空状态 (30s)", "展示欢迎页和功能布局"),
        ("2. 深度研究 (3min)",
         "输入'Transformer相比LSTM有哪些优势？'→Stepper四阶段→左侧拆解的子问题和评分→右侧报告流式生成→来源引用卡片"),
        ("3. 快速检索 (1min)", "侧边栏「快速检索」→输入问题→秒级回复+AI摘要"),
        ("4. 资料管理 (1min)", "「资料管理」→上传PDF→自动索引→预览/删除"),
        ("5. 系统设置 (30s)", "「系统设置」→展示LLM/嵌入/检索配置→说明热重载"),
    ]
    for title, desc in steps_mobile:
        pdf.h2(title)
        pdf.body(desc)

    # ── Self-Intro ──
    pdf.separator()
    pdf.h1("八、自我介绍模板（2-3分钟）")
    pdf.highlight_box(
        "我开发了一个基于Agentic RAG的深度研究Agent，核心价值是让Agent具备主动研究能力。"
        "技术上用LangGraph StateGraph做显式状态编排——定义了拆解、检索、评估、合成四个节点和一个条件路由。"
        "检索层是混合检索，向量+BM25+RRF融合，Agent会根据问题特征自主选择检索策略。"
        "最核心的是自我纠错机制——检索质量不达标时，自动改写查询、切换策略，最多3次升级重试。"
        "后端FastAPI+SSE流式推送，前端Vue 3+TypeScript做了完整的工程化落地——四个功能模块、34个前端文件、12+REST端点。"
        "整个项目47次渐进式提交，从设计文档到代码都有完整记录。"
    )

    # ── Deep Questions ──
    pdf.add_page()
    pdf.h1("九、进阶追问预案")
    deep_qa_mobile = [
        ("为什么不直接用LangChain的create_retrieval_chain？",
         "那是单次检索+回答模式。我的场景需要多步推理——拆解成子问题、每个独立检索评估、失败后重试。create_retrieval_chain做不到这个闭环。"),
        ("ChromaDB数据量大了怎么办？",
         "ChromaDB适合10万级chunks。更大场景可替换为Milvus——VectorStore是抽象接口，切换只需改一个类。配置里已预留MILVUS_前缀。"),
        ("多轮对话怎么设计？",
         "Pinia chat store维护对话历史，作为research请求的context参数传入后端。SSE事件流天然支持追加。"),
        ("如果LLM挂了怎么处理？",
         "所有LLM调用有exception捕获+SSE error事件。多Provider架构（Factory模式）可通过配置快速切换备用Provider。"),
    ]
    for q, a in deep_qa_mobile:
        pdf.qa_item(q, a)

    # ── Save ──
    os.makedirs(os.path.dirname(OUTPUT_MOBILE), exist_ok=True)
    pdf.output(OUTPUT_MOBILE)
    print(f"Mobile PDF generated: {OUTPUT_MOBILE}")
    print(f"Pages: {pdf.page_no()}")


if __name__ == "__main__":
    build()
    build_mobile()
