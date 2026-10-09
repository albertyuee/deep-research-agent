# Reproducible evaluation reporting

The repository contains evaluation tooling, but this document does not claim a completed retrieval benchmark. Publish results only after retaining the corresponding run report.

Record the Git commit, date, public corpus version, document/chunk and question counts, embedding model, vector backend, retrieval settings, reranker, cache conditions and execution environment. Save the command and sanitized machine-readable results.

## Compare one variable at a time

Use the same corpus, questions and model configuration for vector-only, hybrid and hybrid-plus-reranking comparisons. Confirm that the script exposes the intended mode before describing a run as an ablation. Report unsupported modes as future work, not measured results.

| Configuration | Cases | Hit@5 | MRR | Source recall | Mean latency |
| --- | --- | --- | --- | --- | --- |
| Vector only | Not run | — | — | — | — |
| Hybrid | Not run | — | — | — | — |
| Hybrid + reranking | Not run | — | — | — | — |

Retrieval hit rate is not answer accuracy. Evaluate citation support and final-answer correctness separately. Include failures and acknowledge small samples. Do not tune on a held-out set and then describe it as independent evaluation.

## Run

After indexing the public corpus, run from the repository root:

```bash
.venv/bin/python scripts/evaluate_retrieval.py --top-k 5 --output reports/retrieval-evaluation.json
```

Check provider configuration first: evaluation can call external APIs and incur charges. Do not publish private uploads, secrets or restricted benchmark corpora with reports.
