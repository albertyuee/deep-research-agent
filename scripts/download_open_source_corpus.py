"""Download a small, license-tracked corpus for local retrieval testing.

The corpus contains only upstream README files from projects with explicit
open-source or open-content licenses. Each local document is wrapped with
source and license metadata so citations remain auditable.
"""

from __future__ import annotations

import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class CorpusSource:
    slug: str
    title: str
    project_url: str
    raw_url: str
    license_name: str
    license_url: str
    suggested_question: str


SOURCES = (
    CorpusSource(
        slug="microsoft_graphrag",
        title="Microsoft GraphRAG",
        project_url="https://github.com/microsoft/graphrag",
        raw_url="https://raw.githubusercontent.com/microsoft/graphrag/main/README.md",
        license_name="MIT",
        license_url="https://github.com/microsoft/graphrag/blob/main/LICENSE",
        suggested_question="GraphRAG 与传统向量 RAG 的处理方式有什么区别？",
    ),
    CorpusSource(
        slug="langchain_langgraph",
        title="LangGraph",
        project_url="https://github.com/langchain-ai/langgraph",
        raw_url="https://raw.githubusercontent.com/langchain-ai/langgraph/main/README.md",
        license_name="MIT",
        license_url="https://github.com/langchain-ai/langgraph/blob/main/LICENSE",
        suggested_question="LangGraph 如何支持有状态、可恢复的 Agent 工作流？",
    ),
    CorpusSource(
        slug="deepset_haystack",
        title="Haystack",
        project_url="https://github.com/deepset-ai/haystack",
        raw_url="https://raw.githubusercontent.com/deepset-ai/haystack/main/README.md",
        license_name="Apache-2.0",
        license_url="https://github.com/deepset-ai/haystack/blob/main/LICENSE",
        suggested_question="Haystack 的 Pipeline 与 Agent 能力分别适合什么场景？",
    ),
    CorpusSource(
        slug="llamaindex",
        title="LlamaIndex",
        project_url="https://github.com/run-llama/llama_index",
        raw_url="https://raw.githubusercontent.com/run-llama/llama_index/main/README.md",
        license_name="MIT",
        license_url="https://github.com/run-llama/llama_index/blob/main/LICENSE",
        suggested_question="LlamaIndex 在私有数据与大模型之间承担什么角色？",
    ),
    CorpusSource(
        slug="chroma",
        title="Chroma",
        project_url="https://github.com/chroma-core/chroma",
        raw_url="https://raw.githubusercontent.com/chroma-core/chroma/main/README.md",
        license_name="Apache-2.0",
        license_url="https://github.com/chroma-core/chroma/blob/main/LICENSE",
        suggested_question="Chroma 为 AI 应用提供了哪些检索和向量存储能力？",
    ),
    CorpusSource(
        slug="qdrant",
        title="Qdrant",
        project_url="https://github.com/qdrant/qdrant",
        raw_url="https://raw.githubusercontent.com/qdrant/qdrant/master/README.md",
        license_name="Apache-2.0",
        license_url="https://github.com/qdrant/qdrant/blob/master/LICENSE",
        suggested_question="Qdrant 的过滤、混合查询和分布式能力适合哪些 RAG 场景？",
    ),
    CorpusSource(
        slug="hotpotqa",
        title="HotpotQA",
        project_url="https://github.com/hotpotqa/hotpot",
        raw_url="https://raw.githubusercontent.com/hotpotqa/hotpot/master/README.md",
        license_name="CC BY-SA 4.0 (dataset) / Apache-2.0 (code)",
        license_url="https://github.com/hotpotqa/hotpot#license",
        suggested_question="HotpotQA 如何通过 supporting facts 评估多跳问答？",
    ),
)


def download_text(url: str) -> str:
    """Download through curl so macOS system proxy settings are respected."""
    try:
        result = subprocess.run(
            [
                "curl",
                "-fsSL",
                "--retry",
                "3",
                "--connect-timeout",
                "10",
                "--max-time",
                "45",
                "-A",
                "DeepResearchAgent/0.1 (open-source corpus downloader)",
                url,
            ],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"Failed to download {url}: {error}") from error
    return result.stdout.decode("utf-8")


def wrap_document(source: CorpusSource, upstream_text: str) -> str:
    retrieved = date.today().isoformat()
    clean_upstream = "\n".join(line.rstrip() for line in upstream_text.strip().splitlines())
    return f"""---
title: {source.title}
source_url: {source.project_url}
license: {source.license_name}
license_url: {source.license_url}
retrieved_at: {retrieved}
---

# {source.title}：开源项目资料

> 来源：[{source.project_url}]({source.project_url})
> 许可证：[{source.license_name}]({source.license_url})
> 获取日期：{retrieved}

以下内容来自项目上游 README，用于本地检索与研究测试。

---

{clean_upstream}
"""


def build_manifest(output_dir: Path, downloaded: list[tuple[CorpusSource, Path]]) -> str:
    lines = [
        "# 开放许可测试语料清单",
        "",
        f"生成日期：{date.today().isoformat()}",
        "",
        "这套语料用于测试快速检索、深度研究和多跳推理。上游内容的权利与许可证归各项目所有。",
        "",
        "## 文件与许可证",
        "",
        "| 文件 | 项目 | 许可证 | 上游来源 |",
        "|---|---|---|---|",
    ]
    for source, path in downloaded:
        lines.append(
            f"| `{path.name}` | {source.title} | [{source.license_name}]({source.license_url}) "
            f"| [GitHub]({source.project_url}) |"
        )

    lines.extend(["", "## 建议测试问题", ""])
    for source, _ in downloaded:
        lines.append(f"- {source.suggested_question}")
    lines.extend([
        "- GraphRAG、LangGraph、Haystack 和 LlamaIndex 在一套深度研究系统中可以分别承担什么职责？",
        "- 如果要构建支持过滤和多跳推理的 RAG，Qdrant、Chroma 与 HotpotQA 分别能提供什么？",
        "",
        "## 说明",
        "",
        "- 文档内容可能随上游仓库更新；本清单记录了本次下载日期。",
        "- 测试时可以先关闭联网搜索，以确认回答确实来自本地知识库。",
        "- 引用或再分发时请遵守每个项目对应的许可证要求。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="data/open_source_docs",
        help="Directory for downloaded Markdown files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[tuple[CorpusSource, Path]] = []

    print(f"Downloading {len(SOURCES)} sources in parallel...", flush=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        upstream_documents = list(executor.map(download_text, (source.raw_url for source in SOURCES)))

    for source, text in zip(SOURCES, upstream_documents, strict=True):
        destination = output_dir / f"{source.slug}.md"
        destination.write_text(wrap_document(source, text), encoding="utf-8")
        downloaded.append((source, destination))
        print(f"  {destination} ({destination.stat().st_size:,} bytes)", flush=True)

    manifest_path = output_dir / "SOURCE_MANIFEST.md"
    manifest_path.write_text(build_manifest(output_dir, downloaded), encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")
    print(f"Downloaded {len(downloaded)} open-source documents.")


if __name__ == "__main__":
    main()
