## MODIFIED Requirements

### Requirement: Real-time SSE event log
The frontend SHALL display a real-time event log panel that lists all SSE events in chronological order.

The event log SHALL be rendered in the Streamlit sidebar (`st.sidebar`) instead of the main progress panel, freeing up space in the primary view for core progress information.

The event log SHALL include:
- Relative timestamp (seconds since task started)
- Event type name
- Key data summary for each event

The event log SHALL be collapsible via a toggle, and SHALL be collapsed by default.

Each event entry SHALL be expandable to show the full raw payload data.

#### Scenario: Event log appears in sidebar during research
- **WHEN** a research task is running and SSE events are being received
- **THEN** the event log panel is available in the sidebar
- **AND** it lists all events received so far, with timestamps relative to task start

#### Scenario: Event log updates in real-time
- **WHEN** a new SSE event arrives
- **THEN** the event log appends the new event entry
- **AND** the timestamp reflects elapsed time since the first event

#### Scenario: Event log default collapsed
- **WHEN** a new research task starts
- **THEN** the event log panel is collapsed (folded) by default
- **AND** user can click to expand and view events

#### Scenario: Expand single event detail
- **WHEN** user clicks on an individual event entry in the log
- **THEN** the full raw data payload for that event is displayed

#### Scenario: Sidebar empty when not running
- **WHEN** no research task is running and no previous task data exists
- **THEN** the sidebar displays a brief hint text or is empty

---

### Requirement: Phase timing statistics
The frontend SHALL display per-phase timing statistics showing how long each agent phase took.

Phases tracked SHALL include: decomposition, retrieval (per step), critique (per step), and synthesis.

Each phase's duration SHALL be calculated from the timestamp difference between the phase's start event and its completion event.

The timing statistics panel SHALL be rendered in the Streamlit sidebar (`st.sidebar`) alongside the event log, rather than in the main progress panel.

#### Scenario: Timing stats show after research completes
- **WHEN** a research task completes (done event received)
- **THEN** timing statistics for each phase are displayed in the sidebar
- **AND** total elapsed time is shown

#### Scenario: Timing stats update during research
- **WHEN** a phase completes (e.g., retrieval_result event received)
- **THEN** that phase's duration is updated in the timing stats in the sidebar

---

### Requirement: Detailed retry history display
The frontend SHALL display a retry history section when retrieval retries occur.

For each retry SHALL be shown:
- The retry attempt number
- The composite critique score that triggered the retry
- The retry query/suggestion used

The retry history SHALL be rendered in the Streamlit sidebar (`st.sidebar`) when visible.

The retry history SHALL only be visible when at least one retry has occurred.

#### Scenario: Retry history visible after retries
- **WHEN** one or more retrieval retries have been triggered
- **THEN** a retry history panel is displayed in the sidebar
- **AND** each retry shows attempt number, score at retry time, and retry suggestion

#### Scenario: No retry history when no retries
- **WHEN** all retrieval steps passed on first attempt
- **THEN** no retry history panel is displayed
