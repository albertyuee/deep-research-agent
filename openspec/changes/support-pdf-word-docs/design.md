## Context

当前项目的数据摄入完全依赖手动编程：用户需编写 Python 脚本，手动读取文件、按段落分块、分别调用 `VectorStore.add_documents()` 和 `BM25Retriever.index_documents()` 完成索引。只支持纯文本/Markdown 格式，PDF 和 Word 文档需要用户自行用外部工具转换为文本。

LangChain 社区已有成熟的 Document Loader 生态（`PyMuPDFLoader`、`Docx2txtLoader`），本项目不需要重新造轮子，可以直接复用这些 loader 并封装为项目统一的加载接口。

## Goals / Non-Goals

**Goals:**
- 提供统一的 `DocumentLoader` 类，支持 `.pdf`、`.docx`、`.md`、`.txt` 四种格式
- 自动检测文件类型，根据扩展名选择合适的解析器
- 支持单文件和批量目录两种加载模式
- 保留文档元信息（文件名、来源路径、页数等）作为 metadata
- 提供 `scripts/index_documents.py` 一键索引脚本，降低使用门槛
- PDF 使用 PyMuPDF（fitz）、Word 使用 python-docx 解析

**Non-Goals:**
- 不支持 `.doc`（旧版 Word 格式，占比极低）
- 不支持 OCR（扫描件 PDF 的文字识别）
- 不支持图片、表格的结构化提取（作为纯文本提取即可）
- 不修改现有检索流程的任何逻辑
- 不提供 Web UI 上传功能（V2 规划）

## Decisions

### 1. PDF 解析库：PyMuPDF (fitz)

**选择**：PyMuPDF，而非 pdfplumber 或 PyPDF2
**理由**：
- PyMuPDF 解析速度快（C 底层），对大文档友好
- 对中英文混合文档支持好
- pdfplumber 侧重于表格提取（超出当前需求），PyPDF2 功能最弱
- PyMuPDF 将不支持的字符用空格/占位符替代，不会崩溃

### 2. Word 解析库：python-docx

**选择**：python-docx
**理由**：
- 事实上的标准库，社区活跃
- 纯 Python 实现，无系统依赖
- 只支持 `.docx`（Office 2007+），`.doc` 已极少见

### 3. 模块位置：`research_agent/retrieval/document_loader.py`

**选择**：放在 retrieval 包下，而非新建独立模块
**理由**：
- 文档加载是检索的前置步骤，语义上属于 retrieval 管道
- 与 `vector_store.py`、`bm25.py` 保持在同一包，方便索引脚本引用
- 避免过早膨胀项目目录结构

### 4. 分块策略：简单段落分块

**选择**：按 `\n\n` 分块 + 最小长度过滤（50 字符），与现有示例脚本一致
**非目标**：不在此次变更中引入语义分块（如 LangChain 的 `RecursiveCharacterTextSplitter`），作为后续优化项

### 5. 索引脚本位置：`scripts/index_documents.py`

**选择**：项目根目录下新建 `scripts/` 目录
**理由**：
- 脚本不属于 research_agent 核心逻辑，不适合放在包内
- 与 data/sample_docs 区分开（data 放数据，scripts 放工具）
- 命令行参数方式调用，方便 CI/定时任务集成

## Risks / Trade-offs

- **[风险] PyMuPDF 对某些中文 PDF 可能乱码** → 已在 embedding.py 已知中文 BGE 模型 1024 维有效，PyMuPDF 对 UTF-8 中文支持成熟；极端情况下提供 fallback 提示用户手动转换
- **[风险] 大文件内存占用** → 分块策略确保单次加载后即释放原始文本；如后续遇到百 MB 级 PDF，再引入流式加载
- **[取舍] 不引入 LangChain Document Loader 复用** → 直接使用底层库（PyMuPDF、python-docx），减少依赖链长度，与项目当前"不引入 langchain 做检索编排"的决策一致
