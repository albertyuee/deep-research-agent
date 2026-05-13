## ADDED Requirements

### Requirement: Multi-source result aggregation
The system SHALL aggregate retrieval results from all sub-questions, deduplicate overlapping information, and resolve contradictions between sources.

#### Scenario: Overlapping results deduplicated
- **WHEN** two sub-questions retrieve chunks covering the same information
- **THEN** final report mentions the information once, citing both sources

#### Scenario: Contradictory results flagged
- **WHEN** two sources provide conflicting information on the same point
- **THEN** report includes both perspectives with source citations and a conflict note

### Requirement: Structured report generation
The system SHALL generate a structured report with: title, executive summary (2-3 sentences), per-question findings with inline citations, and a references section listing all cited sources.

#### Scenario: Complete report structure
- **WHEN** synthesis completes
- **THEN** report contains `## 研究摘要`, `## 详细发现` (per sub-question), `## 参考资料` sections

### Requirement: Inline source citations
The system SHALL attach source metadata (document title, chunk index, retrieval score, retrieval strategy) to every factual claim in the report.

#### Scenario: Claim with citation
- **WHEN** report states a specific fact from retrieved documents
- **THEN** the fact is followed by a citation marker `[来源: doc_title, chunk_3, score=0.87]`

### Requirement: Report synthesis streaming
The system SHALL stream report generation via SSE events (`synthesis_start`, `synthesis_chunk`).

#### Scenario: Report streams in real-time
- **WHEN** synthesis begins
- **THEN** frontend receives `synthesis_start`, then `synthesis_chunk` events containing incremental report text
