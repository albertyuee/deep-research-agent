"""Evaluate the configured knowledge-base retriever against a fixed dataset.

Usage:
    .venv/bin/python scripts/evaluate_retrieval.py
    .venv/bin/python scripts/evaluate_retrieval.py --top-k 10 --output reports/retrieval.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_DATASET = PROJECT_ROOT / "data" / "evaluation" / "retrieval_cases.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate hybrid retrieval quality")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-hit-rate", type=float, default=0.75)
    parser.add_argument("--min-source-recall", type=float, default=0.75)
    parser.add_argument("--output", type=Path, help="Optional path for the JSON report")
    args = parser.parse_args()

    if args.top_k < 1 or args.top_k > 100:
        parser.error("--top-k must be between 1 and 100")

    from research_agent.evaluation import load_cases, run_retrieval_evaluation
    from research_agent.retrieval.service import retrieval_service

    cases = load_cases(args.dataset)
    retriever = retrieval_service.get_hybrid()
    report = run_retrieval_evaluation(
        cases,
        lambda query, top_k: retriever.search(query, top_k=top_k),
        top_k=args.top_k,
    )

    for item in report["cases"]:
        status = "PASS" if item["hit_at_k"] else "FAIL"
        ranks = ", ".join(
            f"{source}={rank or '-'}" for source, rank in item["source_ranks"].items()
        )
        print(f"[{status}] {item['id']}: {ranks} ({item['latency_ms']:.1f} ms)")

    summary = report["summary"]
    print("\nSummary")
    print(f"  Cases:          {summary['case_count']}")
    print(f"  Hit@1:          {summary['hit_at_1_rate']:.1%}")
    print(f"  Hit@{summary['top_k']}:          {summary['hit_at_k_rate']:.1%}")
    print(f"  MRR:            {summary['mean_reciprocal_rank']:.4f}")
    print(f"  Source recall:  {summary['mean_source_recall']:.1%}")
    print(f"  Avg latency:    {summary['average_latency_ms']:.1f} ms")

    if args.output:
        output_path = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Report:         {output_path}")

    passed = (
        summary["hit_at_k_rate"] >= args.min_hit_rate
        and summary["mean_source_recall"] >= args.min_source_recall
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
