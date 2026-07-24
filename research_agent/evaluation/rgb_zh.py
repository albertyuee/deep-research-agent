"""Prepare Chinese multi-hop retrieval cases from the RGB zh_int benchmark."""

from __future__ import annotations

import json
import random
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load the RGB dataset, whose .json files contain one JSON object per line."""
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid RGB JSONL at line {line_number}: {exc}") from exc
            if isinstance(row, dict):
                rows.append(row)
    if not rows:
        raise ValueError("RGB dataset is empty")
    return rows


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        text = " ".join(value.split())
        return [text] if text else []
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_strings(item))
        return flattened
    return []


def _positive_groups(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    groups: list[list[str]] = []
    for item in value:
        group = _flatten_strings(item)
        if group:
            groups.append(group)
    return groups


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _bounded_passage(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    return normalized[:max_chars].rstrip()


def _answer_terms(row: dict[str, Any], evidence_index: int) -> list[str]:
    """Read RGB's per-hop answers, including its historical asnwer1 typo."""
    field_names = (
        ("answer1", "asnwer1")
        if evidence_index == 1
        else ("answer2",)
    )
    for field_name in field_names:
        terms = _flatten_strings(row.get(field_name))
        if terms:
            return terms

    combined = row.get("answer")
    if isinstance(combined, list) and len(combined) >= evidence_index:
        return _flatten_strings(combined[evidence_index - 1])
    return []


def _select_evidence_passage(
    row: dict[str, Any], group: list[str], evidence_index: int
) -> str:
    answer_terms = _answer_terms(row, evidence_index)
    matching = [
        passage
        for passage in group
        if any(term and term in passage for term in answer_terms)
    ]
    if not matching:
        return max(group, key=len)

    conclusion_cues = ("是", "为", "夺得", "获得", "赢得", "击败", "冠军", "时间为", "开始于", "结束于")

    def evidence_strength(passage: str) -> tuple[int, int, int]:
        proximity_hits = 0
        for term in answer_terms:
            escaped = re.escape(term)
            for cue in conclusion_cues:
                if re.search(rf"{escaped}.{{0,60}}{re.escape(cue)}", passage):
                    proximity_hits += 1
                if re.search(rf"{re.escape(cue)}.{{0,60}}{escaped}", passage):
                    proximity_hits += 1
        cue_count = sum(passage.count(cue) for cue in conclusion_cues)
        return proximity_hits, cue_count, len(passage)

    return max(matching, key=evidence_strength)


def build_artifacts(
    rows: list[dict[str, Any]],
    sample_size: int = 8,
    seed: int = 42,
    distractors_per_case: int = 4,
    max_passage_chars: int = 1800,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build corpus records and two-source retrieval cases without answer leakage."""
    candidates = [
        row
        for row in rows
        if _contains_chinese(str(row.get("query", "")))
        and len(_positive_groups(row.get("positive"))) >= 2
    ]
    if len(candidates) < sample_size:
        raise ValueError(
            f"RGB dataset only has {len(candidates)} usable rows, fewer than sample_size={sample_size}"
        )

    rng = random.Random(seed)
    selected = rng.sample(candidates, sample_size)
    corpus: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []

    for position, row in enumerate(selected, start=1):
        raw_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(row.get("id", position))).strip("-")
        case_id = f"rgb_zh_int_{raw_id or position}"
        groups = _positive_groups(row.get("positive"))
        expected_sources: list[str] = []
        selected_evidence: set[str] = set()

        for evidence_index, group in enumerate(groups[:2], start=1):
            # RGB provides several positive candidates per hop. Prefer a
            # passage containing that hop's annotated answer; otherwise retain
            # the longest cleaned passage as a deterministic fallback.
            passage = _select_evidence_passage(row, group, evidence_index)
            selected_evidence.add(passage)
            file_name = f"{case_id}_evidence_{evidence_index}.txt"
            expected_sources.append(file_name)
            corpus.append({
                "chunk_id": file_name.removesuffix(".txt"),
                "file_name": file_name,
                "doc_title": f"RGB 中文多跳题 {position} 必要证据 {evidence_index}",
                "content": _bounded_passage(passage, max_passage_chars),
                "case_id": case_id,
                "evidence_role": "supporting",
            })

        negatives = [
            passage
            for passage in _flatten_strings(row.get("negative", []))
            if passage not in selected_evidence
        ]
        rng.shuffle(negatives)
        for distractor_index, passage in enumerate(
            negatives[: max(0, distractors_per_case)], start=1
        ):
            file_name = f"{case_id}_distractor_{distractor_index}.txt"
            corpus.append({
                "chunk_id": file_name.removesuffix(".txt"),
                "file_name": file_name,
                "doc_title": f"RGB 中文多跳题 {position} 干扰证据 {distractor_index}",
                "content": _bounded_passage(passage, max_passage_chars),
                "case_id": case_id,
                "evidence_role": "distractor",
            })

        cases.append({
            "id": case_id,
            "query": str(row["query"]).strip(),
            "expected_sources": expected_sources,
            "match": "all",
            "expected_answer": row.get("answer", []),
        })

    return corpus, cases
