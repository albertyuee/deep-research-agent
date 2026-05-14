## Why

当前项目仅支持手动将 Markdown/纯文本文件分块后索引到向量库和 BM25，无法直接处理 PDF 和 Word（.docx）这两种最常见的文档格式。实际使用场景中，用户的研究资料大量以 PDF 论文、Word 报告形式存在，每次都需要手动转换为纯文本再索引，使用门槛太高。

## What Changes

- 新增 `research_agent/retrieval/document_loader.py`：统一文档加载模块，支持 PDF（.pdf）和 Word（.docx）格式的自动解析与文本提取
- 新增 `scripts/index_documents.py`：一键索引脚本，指定目录后自动扫描支持的文档、解析、分块、索引到向量库和 BM25
- 新增依赖：`PyMuPDF`（PDF 解析）、`python-docx`（Word 解析）
- 更新 `pyproject.toml`：添加新依赖
- 更新 `README.md`：在快速开始中增加 PDF/Word 文档索引说明

## Capabilities

### New Capabilities
- `document-loading`: 统一文档加载接口，支持 PDF（.pdf）和 Word（.docx）格式，自动检测文件类型并提取文本内容，保留文档元信息（文件名、页数等）作为 metadata

### Modified Capabilities
<!-- 无已有 spec 需要修改 -->

## Impact

- 新增文件：`research_agent/retrieval/document_loader.py`、`scripts/index_documents.py`
- 修改文件：`pyproject.toml`、`README.md`
- 新增依赖：`PyMuPDF>=1.24.0`、`python-docx>=1.1.0`
- 无 API 变更，无 breaking changes
- 现有检索流程（向量库 + BM25 + 混合检索）不变，仅扩展上游文档来源
