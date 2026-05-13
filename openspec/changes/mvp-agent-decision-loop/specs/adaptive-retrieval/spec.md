## ADDED Requirements

### Requirement: Hybrid retrieval with strategy selection
The system SHALL support vector search (BGE-large-v2) and BM25 keyword search, and the agent SHALL autonomously select the strategy based on the sub-query characteristics.

#### Scenario: Conceptual question uses vector search
- **WHEN** sub-query is "人工智能对医疗行业的影响是什么？"
- **THEN** agent selects "semantic" strategy and uses vector similarity search

#### Scenario: Terminology question uses BM25
- **WHEN** sub-query contains specific entity names or numbers like "IL-6 抑制剂 2023 年临床试验"
- **THEN** agent selects "keyword" strategy and uses BM25 search

#### Scenario: Ambiguous query uses hybrid
- **WHEN** sub-query type is unclear
- **THEN** agent defaults to "hybrid" strategy with RRF fusion (k=60)

### Requirement: Retrieval quality self-assessment
After retrieval, the system SHALL evaluate the quality of results and record a confidence score (0-1) based on relevance and coverage.

#### Scenario: High-quality retrieval passes
- **WHEN** retrieved chunks have high semantic similarity to the query AND cover all key information points
- **THEN** confidence score > 0.6 and results proceed to synthesis

#### Scenario: Low-quality retrieval triggers retry
- **WHEN** retrieved chunks have low similarity or incomplete coverage
- **THEN** confidence score < 0.6 and system triggers retry with adjusted strategy

### Requirement: Query rewriting on retry
The system SHALL rewrite the search query on each retry attempt, adjusting breadth or specificity based on previous failure.

#### Scenario: First retry broadens query
- **WHEN** initial retrieval returned too few results
- **THEN** query is rewritten to be broader (e.g., remove specific constraints)

#### Scenario: Second retry switches strategy
- **WHEN** first retry with same strategy also fails
- **THEN** strategy is switched (vector → keyword or vice versa)

### Requirement: Retrieval streaming
The system SHALL stream retrieval progress via SSE events (`retrieval_start`, `retrieval_result`).

#### Scenario: Retrieval progress visible
- **WHEN** retrieval begins for a sub-question
- **THEN** frontend receives `retrieval_start` with sub-question index, then `retrieval_result` with result count and top chunk preview
