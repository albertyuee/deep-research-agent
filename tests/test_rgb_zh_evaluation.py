"""Tests for preparing Chinese RGB multi-hop retrieval artifacts."""

import json

from research_agent.evaluation.rgb_zh import build_artifacts, load_jsonl


def _row(row_id: int) -> dict:
    return {
        "id": row_id,
        "query": f"中文多跳问题 {row_id}",
        "answer": ["答案一", "答案二"],
        "positive": [
            [
                f"很长但没有标准答案的候选文章 {row_id}。" * 20,
                f"第一跳必要证据包含答案一 {row_id}。",
            ],
            [f"第二跳必要证据 {row_id}。" * 10],
        ],
        "negative": [f"干扰资料 {row_id}-{index}" for index in range(4)],
    }


def test_load_rgb_jsonl(tmp_path):
    path = tmp_path / "zh_int.jsonl"
    path.write_text("\n".join(json.dumps(_row(i), ensure_ascii=False) for i in range(2)), encoding="utf-8")

    rows = load_jsonl(path)

    assert len(rows) == 2
    assert rows[0]["query"].startswith("中文多跳问题")


def test_build_artifacts_requires_two_sources_and_keeps_answers_out_of_corpus():
    corpus, cases = build_artifacts(
        [_row(i) for i in range(5)],
        sample_size=2,
        seed=7,
        distractors_per_case=2,
    )

    assert len(cases) == 2
    assert len(corpus) == 8
    assert all(case["match"] == "all" for case in cases)
    assert all(len(case["expected_sources"]) == 2 for case in cases)
    assert all(record["evidence_role"] in {"supporting", "distractor"} for record in corpus)
    assert all("expected_answer" not in record for record in corpus)
    supporting_texts = [
        record["content"] for record in corpus if record["evidence_role"] == "supporting"
    ]
    assert all("答案一" in text for text in supporting_texts[::2])
