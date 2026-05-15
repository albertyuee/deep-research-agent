## ADDED Requirements

### Requirement: Enter key submission via form
The query input area SHALL be wrapped in a `st.form` component so that pressing Enter while focused on the text input submits the research task.

The form SHALL contain:
- A text area for research question input
- A submit button labeled "Start Research"

The form SHALL be disabled while a research task is already running.

#### Scenario: Enter submits the form
- **WHEN** user types a question in the text area and presses Enter
- **THEN** the form submits and the research task begins
- **AND** no separate click on the submit button is required

#### Scenario: Form disabled during research
- **WHEN** a research task is running (is_running = True)
- **THEN** the form and all its inputs are disabled

#### Scenario: Empty input prevents submission
- **WHEN** the text area is empty or contains only whitespace
- **THEN** the submit button is disabled
- **AND** pressing Enter does not trigger submission

---

### Requirement: Example query chip interaction with form
Example query chips SHALL be placed outside the form and, when clicked, SHALL populate the form's text input with the chip's question text.

The populated text SHALL appear in the text area, and the user SHALL still need to press Enter or click submit to begin the research.

#### Scenario: Chip click fills text area
- **WHEN** user clicks an example query chip
- **THEN** the form's text area is filled with the chip's question text
- **AND** the research does NOT start automatically
- **AND** the user can edit the text before submitting

---

### Requirement: Progress bar with real backend data
The progress bar SHALL reflect actual research progress by reading a `progress` field from SSE events sent by the backend.

The `progress` field SHALL be a float between 0.0 and 1.0 representing the estimated completion percentage. If the field is absent, the frontend SHALL fall back to estimating progress based on the current phase.

The progress bar SHALL reach 1.0 (100%) when the `done` event is received.

#### Scenario: Progress updates from SSE events
- **WHEN** an SSE event contains a `progress` field with value 0.35
- **THEN** the progress bar displays 35% completion

#### Scenario: Progress reaches 100% on done
- **WHEN** the `done` event is received
- **THEN** the progress bar displays 100% completion regardless of the event's progress field value

#### Scenario: Fallback when progress field missing
- **WHEN** SSE events do not contain a `progress` field
- **THEN** the frontend estimates progress based on the current phase:
  - planning: 0.10
  - retrieving (step N of total M): 0.10 + (N/M) * 0.35
  - evaluating: 0.45
  - synthesizing: 0.65
  - done: 1.0
