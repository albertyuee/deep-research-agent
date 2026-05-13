## ADDED Requirements

### Requirement: LangGraph state machine
The system SHALL use LangGraph StateGraph to orchestrate the agent decision loop with 4 nodes (Decomposition → Retrieval → Critique → Synthesis) and conditional routing between them.

#### Scenario: Normal flow without retry
- **WHEN** Critique returns `passed: true`
- **THEN** flow proceeds: Decomposition → Retrieval → Critique → Synthesis → End

#### Scenario: Retry flow
- **WHEN** Critique returns `passed: false` and retry_count < 3
- **THEN** flow proceeds: Critique → Retrieval (retry) → Critique → (repeat until pass or max retries)

### Requirement: Centralized agent state
The system SHALL maintain a single `ResearchState` object that all nodes read from and write to, ensuring state consistency across the agent decision loop.

#### Scenario: State shared across nodes
- **WHEN** Retrieval node writes results to state
- **THEN** Critique node reads the same results from state for evaluation

### Requirement: SSE streaming from all nodes
The system SHALL emit SSE events from each LangGraph node so the frontend can visualize the entire agent decision process in real-time.

#### Scenario: Full agent lifecycle streaming
- **WHEN** a research task runs end-to-end
- **THEN** frontend receives events from all 4 nodes in correct order, with `done` event marking completion

### Requirement: FastAPI research endpoint
The system SHALL expose `POST /research` to submit a research query and return a task ID, and `GET /research/{id}/stream` for SSE subscription.

#### Scenario: Submit research task
- **WHEN** POST to `/research` with `{"query": "..."}`
- **THEN** system returns `{"success": true, "data": {"task_id": "uuid"}}` and starts agent execution

#### Scenario: Stream agent progress
- **WHEN** GET `/research/{id}/stream` with valid task_id
- **THEN** client receives SSE event stream of agent progress

### Requirement: Streamlit frontend
The system SHALL provide a Streamlit web interface with: text input for research query, real-time display of agent thinking steps (decomposition → retrieval → critique → synthesis), final report rendering with markdown, and source citation list.

#### Scenario: End-to-end user interaction
- **WHEN** user enters query and clicks "开始研究"
- **THEN** interface shows streaming agent progress panel AND final report panel
