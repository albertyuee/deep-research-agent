## ADDED Requirements

### Requirement: Multi-dimensional quality scoring
The system SHALL evaluate each retrieval result on two dimensions: relevance (semantic match, 0-1) and completeness (information coverage, 0-1). Composite score = 0.6 × relevance + 0.4 × completeness.

#### Scenario: Relevant but incomplete result
- **WHEN** retrieved chunks are on-topic but only cover 2 out of 4 expected information points
- **THEN** relevance > 0.7, completeness < 0.5, composite < 0.6, retry triggered

#### Scenario: Complete and relevant result
- **WHEN** retrieved chunks are on-topic AND cover all expected information points
- **THEN** both scores > 0.7, composite > 0.6, results pass critique

### Requirement: Retry control with max attempts
The system SHALL retry retrieval at most 3 times, with progressively adjusted strategies on each attempt.

#### Scenario: Succeeds on 3rd retry
- **WHEN** first retrieval scores 0.4 (fail), second scores 0.5 (fail), third scores 0.7 (pass)
- **THEN** results from 3rd attempt proceed to synthesis

#### Scenario: Fails after 3 retries
- **WHEN** all 3 retrieval attempts score below 0.6
- **THEN** system proceeds to synthesis with best available results AND marks report section with low-confidence indicator

### Requirement: Structured critique output
The system SHALL output critique results in structured JSON format including: composite score, relevance score, completeness score, pass/fail decision, and retry recommendations (strategy adjustment, query rewrite suggestion).

#### Scenario: Critique output format
- **WHEN** critique completes
- **THEN** output includes `{"composite": 0.72, "relevance": 0.8, "completeness": 0.6, "passed": true, "retry_suggestion": null}`

### Requirement: Critique streaming
The system SHALL stream critique progress via SSE events (`critique_start`, `critique_result`).

#### Scenario: Critique result visible
- **WHEN** critique completes
- **THEN** frontend receives `critique_result` with score, decision, and retry suggestion
