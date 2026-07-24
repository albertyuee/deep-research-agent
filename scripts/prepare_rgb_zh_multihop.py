"""Download, index, and evaluate the RGB Chinese multi-hop benchmark.

The RGB dataset is licensed CC BY-NC-SA 4.0 and is intended here only for
non-commercial evaluation.

Usage:
    export https_proxy=http://127.0.0.1:7890
    export http_proxy=http://127.0.0.1:7890
    .venv/bin/python scripts/prepare_rgb_zh_multihop.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_URL = "https://raw.githubusercontent.com/chen700564/RGB/master/data/zh_int.json"
SOURCE_PAGE = "https://github.com/chen700564/RGB"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "rgb_zh_multihop"


def _download(source_url: str, destination: Path, force: bool = False) -> None:
    if destination.exists() and not force:
        print(f"✓ 已存在，跳过下载：{destination}")
        return

    import httpx

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    try:
        timeout = httpx.Timeout(180.0, connect=30.0)
        with httpx.Client(follow_redirects=True, timeout=timeout, trust_env=True) as client:
            with client.stream("GET", source_url) as response:
                response.raise_for_status()
                with temporary.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"✓ 下载完成：{destination}（{destination.stat().st_size / 1024 / 1024:.1f} MB）")


def _write_artifacts(
    output_dir: Path,
    corpus: list[dict],
    cases: list[dict],
    sample_size: int,
    seed: int,
) -> tuple[Path, Path]:
    corpus_path = output_dir / "corpus.jsonl"
    cases_path = output_dir / "retrieval_cases.json"
    manifest_path = output_dir / "SOURCE_MANIFEST.md"

    with corpus_path.open("w", encoding="utf-8") as handle:
        for record in corpus:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    cases_path.write_text(
        json.dumps(
            {
                "version": 1,
                "dataset": "RGB zh_int",
                "license": "CC BY-NC-SA 4.0（仅限非商业测试）",
                "cases": cases,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        "\n".join([
            "# RGB 中文多跳测试语料",
            "",
            f"- 上游项目：{SOURCE_PAGE}",
            f"- 原始数据：{SOURCE_URL}",
            f"- 许可证：CC BY-NC-SA 4.0（仅限非商业测试） {LICENSE_URL}",
            f"- 固定抽样：{sample_size} 道题，随机种子 {seed}",
            f"- 生成语料：{len(corpus)} 个段落",
            "- 说明：知识库语料不写入问题和标准答案，避免答案泄漏。",
            "",
        ]),
        encoding="utf-8",
    )
    return corpus_path, cases_path


def _index_corpus(corpus: list[dict]) -> tuple[int, int]:
    from research_agent.retrieval.search_text import INDEX_VERSION
    from research_agent.retrieval.vector_store import create_vector_store

    store = create_vector_store()
    all_ids, _, all_metadatas = store.get_all_documents()
    previous_ids = [
        chunk_id
        for chunk_id, metadata in zip(all_ids, all_metadatas)
        if metadata.get("dataset") == "rgb_zh_int"
    ]
    deleted = store.delete_by_chunk_ids(previous_ids)

    ids = [record["chunk_id"] for record in corpus]
    texts = [record["content"] for record in corpus]
    metadatas = [
        {
            "file_name": record["file_name"],
            "doc_title": record["doc_title"],
            "source": "RGB zh_int",
            "source_url": SOURCE_PAGE,
            "dataset": "rgb_zh_int",
            "case_id": record["case_id"],
            "evidence_role": record["evidence_role"],
            "license": "CC BY-NC-SA 4.0",
            "index_version": INDEX_VERSION,
        }
        for record in corpus
    ]
    store.add_documents(ids, texts, metadatas)
    return deleted, len(ids)


def _evaluate(cases_path: Path, top_k: int, output_dir: Path) -> dict:
    from research_agent.evaluation import load_cases, run_retrieval_evaluation
    from research_agent.retrieval.service import retrieval_service

    retrieval_service.reset()
    cases = load_cases(cases_path)
    retriever = retrieval_service.get_hybrid()
    report = run_retrieval_evaluation(
        cases,
        lambda query, limit: retriever.search(query, top_k=limit),
        top_k=top_k,
    )
    report_path = output_dir / "evaluation_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for item in report["cases"]:
        status = "通过" if item["hit_at_k"] else "未通过"
        ranks = "，".join(
            f"{source}=第{rank}名" if rank else f"{source}=未召回"
            for source, rank in item["source_ranks"].items()
        )
        print(f"[{status}] {item['query']}\n  {ranks}")

    summary = report["summary"]
    print("\n评测汇总")
    print(f"  问题数：       {summary['case_count']}")
    print(f"  Hit@1：        {summary['hit_at_1_rate']:.1%}")
    print(f"  Hit@{top_k}：       {summary['hit_at_k_rate']:.1%}")
    print(f"  MRR：          {summary['mean_reciprocal_rank']:.4f}")
    print(f"  双证据召回率： {summary['mean_source_recall']:.1%}")
    print(f"  平均耗时：     {summary['average_latency_ms']:.1f} ms")
    print(f"  完整报告：     {report_path}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="准备并测试 RGB 中文多跳检索语料")
    parser.add_argument("--sample-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--distractors", type=int, default=4)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--prepare-only", action="store_true", help="只下载并生成语料，不写入向量库")
    parser.add_argument("--skip-evaluation", action="store_true", help="写入向量库后不运行召回评测")
    args = parser.parse_args()

    if args.sample_size < 1 or args.sample_size > 100:
        parser.error("--sample-size 必须在 1 到 100 之间")
    if args.distractors < 0 or args.distractors > 20:
        parser.error("--distractors 必须在 0 到 20 之间")
    if args.top_k < 2 or args.top_k > 100:
        parser.error("--top-k 必须在 2 到 100 之间")

    output_dir = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    raw_path = output_dir / "zh_int.jsonl"
    print("RGB 数据许可证：CC BY-NC-SA 4.0，仅限非商业测试。")
    _download(SOURCE_URL, raw_path, force=args.force_download)

    from research_agent.evaluation.rgb_zh import build_artifacts, load_jsonl

    rows = load_jsonl(raw_path)
    corpus, cases = build_artifacts(
        rows,
        sample_size=args.sample_size,
        seed=args.seed,
        distractors_per_case=args.distractors,
    )
    corpus_path, cases_path = _write_artifacts(
        output_dir, corpus, cases, args.sample_size, args.seed
    )
    print(f"✓ 已生成 {len(cases)} 道中文多跳问题、{len(corpus)} 个知识库段落")
    print(f"  语料：{corpus_path}")
    print(f"  问题：{cases_path}")

    if args.prepare_only:
        return 0

    deleted, indexed = _index_corpus(corpus)
    print(f"✓ 已删除旧 RGB 分块 {deleted} 个，写入当前向量库 {indexed} 个")
    if not args.skip_evaluation:
        _evaluate(cases_path, args.top_k, output_dir)
    print("提示：请重启后端，让运行中的 BM25 索引读取新增语料。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
