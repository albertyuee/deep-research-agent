## MODIFIED Requirements

### Requirement: Enhanced retrieval result display
The retrieval detail display SHALL show the number of results returned, the top relevance score, and a content preview of the top result.

The retrieval details SHALL remain in the main left progress panel as a core progress indicator.

Retrieval scores SHALL be color-coded: green for score >= 0.7, orange for 0.4 <= score < 0.7, red for score < 0.4.

#### Scenario: Retrieval shows result details
- **WHEN** a retrieval_result SSE event is received with result_count=5 and top_score=0.85
- **THEN** the UI displays "检索到 5 条结果，最高相似度 0.85"
- **AND** a preview of the top result content (first 200 chars) is available
- **AND** the score 0.85 is displayed in green

#### Scenario: Low retrieval score shown in red
- **WHEN** a retrieval_result SSE event is received with top_score=0.30
- **THEN** the score 0.30 is displayed in red

---

### Requirement: Enhanced critique result display
The critique detail display SHALL show both relevance and completeness scores, plus the LLM's reasoning text.

Critique scores SHALL be color-coded: green for score >= 0.7, orange for 0.4 <= score < 0.7, red for score < 0.4.

The critique details SHALL remain in the main left progress panel.

#### Scenario: Critique shows full scoring breakdown
- **WHEN** a critique_result SSE event is received with relevance=0.8, completeness=0.3, composite_score=0.55
- **THEN** both relevance and completeness scores are displayed individually
- **AND** the reasoning text explaining the scores is shown
- **AND** relevance score 0.8 is displayed in green and completeness score 0.3 is displayed in red

#### Scenario: Failed critique shows retry suggestion
- **WHEN** a critique_result SSE event is received with passed=false and retry_suggestion is present
- **THEN** the retry suggestion text is displayed prominently
- **AND** the composite score is displayed in red if < 0.7

---

### Requirement: Decomposition rationale display
The decomposition detail display SHALL show the strategy selection rationale for each sub-query generated.

The decomposition details SHALL remain in the main left progress panel.

#### Scenario: Research plan shows strategy rationale
- **WHEN** research_plan_chunk events are received with rationale fields
- **THEN** each sub-query entry in the research plan displays the rationale explaining why that strategy was chosen
