## ADDED Requirements

### Requirement: Empty state guide page
The right report panel SHALL display a guide page when no research task has been started and no report exists.

The guide page SHALL include:
- A welcome message with the application name and a brief description
- A 3-step visual flow explaining how to use the application (input question → agent researches → get report)
- A set of clickable example queries that users can click to quickly populate the input field

The guide page SHALL be hidden once a research task starts running or a report is available.

#### Scenario: First visit shows guide
- **WHEN** user opens the application for the first time with no research running
- **THEN** the right panel displays the welcome guide with instructions and example queries

#### Scenario: Guide hidden during research
- **WHEN** user clicks "Start Research" and the task begins running
- **THEN** the guide page is replaced by the streaming report display

#### Scenario: Guide hidden when report exists
- **WHEN** a research task has completed and a report is available
- **THEN** the guide page is replaced by the completed report view

---

### Requirement: Clickable example query chips
The input area SHALL display clickable example query chips below the text input that allow users to quickly populate the input field.

Each chip SHALL display a pre-defined example research question. When clicked, the chip SHALL populate the text input with its question text.

At least 3 example queries SHALL be provided covering different research domains.

#### Scenario: Click chip populates input
- **WHEN** user clicks an example query chip
- **THEN** the text input is populated with the chip's question text
- **AND** the input is ready for editing or submission

#### Scenario: Multiple chips available
- **WHEN** the input area is rendered
- **THEN** at least 3 example query chips are displayed
- **AND** each chip shows a different research question
