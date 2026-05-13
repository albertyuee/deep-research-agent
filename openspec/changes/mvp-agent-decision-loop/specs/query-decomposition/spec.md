## ADDED Requirements

### Requirement: LLM-based query decomposition
The system SHALL decompose a complex user query into 2-5 atomic sub-questions, each independently answerable.

#### Scenario: Complex multi-faceted query
- **WHEN** user submits "人工智能在医疗影像和药物研发中的应用有什么区别？"
- **THEN** system returns at least 2 sub-questions covering medical imaging and drug discovery separately

#### Scenario: Simple single-facet query
- **WHEN** user submits "什么是向量检索？"
- **THEN** system returns exactly 1 sub-question (no unnecessary decomposition)

### Requirement: Structured research plan generation
The system SHALL generate a research plan listing sub-questions in execution order, with a suggested retrieval strategy for each.

#### Scenario: Plan with mixed retrieval strategies
- **WHEN** query contains both conceptual questions and keyword-heavy questions
- **THEN** each plan step includes a `suggested_strategy` field ("semantic" or "keyword" or "hybrid")

### Requirement: Decomposition streaming
The system SHALL stream decomposition progress via SSE events (`research_plan_start`, `research_plan_chunk`) so the user sees the agent's planning in real-time.

#### Scenario: Streaming plan generation
- **WHEN** decomposition begins
- **THEN** frontend receives `research_plan_start` immediately, followed by `research_plan_chunk` events for each sub-question
