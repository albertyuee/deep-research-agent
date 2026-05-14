## ADDED Requirements

### Requirement: Enhanced retrieval result display
The retrieval detail display SHALL show the number of results returned, the top relevance score, and a content preview of the top result.

#### Scenario: Retrieval shows result details
- **WHEN** a retrieval_result SSE event is received with result_count=5 and top_score=0.85
- **THEN** the UI displays "检索到 5 条结果，最高相似度 0.85"
- **AND** a preview of the top result content (first 200 chars) is available

### Requirement: Enhanced critique result display
The critique detail display SHALL show both relevance and completeness scores, plus the LLM's reasoning text.

#### Scenario: Critique shows full scoring breakdown
- **WHEN** a critique_result SSE event is received with relevance=0.8, completeness=0.3, composite_score=0.55
- **THEN** both relevance and completeness scores are displayed individually
- **AND** the reasoning text explaining the scores is shown

#### Scenario: Failed critique shows retry suggestion
- **WHEN** a critique_result SSE event is received with passed=false and retry_suggestion is present
- **THEN** the retry suggestion text is displayed prominently

### Requirement: Decomposition rationale display
The decomposition detail display SHALL show the strategy selection rationale for each sub-query generated.

#### Scenario: Research plan shows strategy rationale
- **WHEN** research_plan_chunk events are received with rationale fields
- **THEN** each sub-query entry in the research plan displays the rationale explaining why that strategy was chosen
