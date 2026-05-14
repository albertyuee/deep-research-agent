## 1. 添加依赖

- [x] 1.1 更新 `pyproject.toml` — 在 dependencies 中添加 `PyMuPDF>=1.24.0` 和 `python-docx>=1.1.0`

## 2. 实现文档加载模块

- [x] 2.1 创建 `research_agent/retrieval/document_loader.py` — 实现 `DocumentLoader` 类
- [x] 2.2 实现 `load_pdf()` — 使用 PyMuPDF 提取 PDF 文本，按页提取后合并
- [x] 2.3 实现 `load_docx()` — 使用 python-docx 提取段落文本
- [x] 2.4 实现 `load_text()` — 读取 .md/.txt 纯文本文件
- [x] 2.5 实现 `load_file()` — 统一入口，根据扩展名自动分发到对应解析方法
- [x] 2.6 实现 `load_directory()` — 递归扫描目录，加载所有支持的文件
- [x] 2.7 实现 `_chunk_text()` — 按 `\n\n` 分块 + 最小长度过滤（默认 50 字符）
- [x] 2.8 为所有 chunk 附加 metadata（source_path, file_name, file_type）

## 3. 实现一键索引脚本

- [x] 3.1 创建 `scripts/index_documents.py` — 命令行脚本
- [x] 3.2 支持位置参数 `directory`（要索引的文档目录）
- [x] 3.3 支持 `--min-chunk-length` 可选参数（默认 50）
- [x] 3.4 支持 `--exclude` 可选参数（glob pattern，如 `*.pdf`）
- [x] 3.5 调用 `DocumentLoader.load_directory()` 加载文档
- [x] 3.6 调用 `VectorStore.add_documents()` 索引到 Chroma
- [x] 3.7 调用 `BM25Retriever.index_documents()` 索引到 BM25
- [x] 3.8 输出进度信息（已处理文件数、chunk 数、向量库总数）

## 4. 更新文档

- [x] 4.1 更新 `README.md` — 在快速开始章节增加 PDF/Word 文档索引的说明
