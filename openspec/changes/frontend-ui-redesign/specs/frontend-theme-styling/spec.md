## ADDED Requirements

### Requirement: Custom CSS styling
The application SHALL inject custom CSS to improve visual hierarchy and aesthetics beyond Streamlit's default theme.

The custom CSS SHALL include:
- Card container styles with white background, rounded corners (12px border-radius), box-shadow, and internal padding
- Score color coding: green for pass (scores >= threshold), red for failure (scores < threshold), orange for warnings
- Stepper indicator styles with horizontal layout, connecting lines between steps, and color-coded status dots
- Example query chip styles with rounded pill shape (20px border-radius) and hover highlight effect
- Section spacing and typography adjustments for better readability

The custom CSS SHALL be injected once at application startup via `st.markdown` with `unsafe_allow_html=True`.

#### Scenario: Cards have visual depth
- **WHEN** content is rendered inside a card container
- **THEN** the content appears with white background, rounded corners, and a subtle box-shadow

#### Scenario: Pass scores shown in green
- **WHEN** a critique result has `passed=true` or composite score >= 0.6
- **THEN** the score is displayed with green color styling

#### Scenario: Fail scores shown in red
- **WHEN** a critique result has `passed=false` or composite score < 0.6
- **THEN** the score is displayed with red color styling

#### Scenario: Stepper shows current and completed steps
- **WHEN** the research is in progress at the retrieval phase
- **THEN** the decomposition step shows as completed with a checkmark
- **AND** the retrieval step shows as active with a loading indicator
- **AND** future steps (critique, synthesis) show as inactive/muted

---

### Requirement: Score color coding
All numeric scores in the UI SHALL be color-coded based on their value to provide immediate visual feedback.

Score thresholds:
- score >= 0.7 SHALL be displayed in green
- 0.4 <= score < 0.7 SHALL be displayed in orange
- score < 0.4 SHALL be displayed in red

This applies to relevance scores, completeness scores, composite scores, and retrieval relevance scores.

#### Scenario: High score is green
- **WHEN** a composite score of 0.85 is displayed
- **THEN** the score text is rendered in green color

#### Scenario: Medium score is orange
- **WHEN** a relevance score of 0.55 is displayed
- **THEN** the score text is rendered in orange color

#### Scenario: Low score is red
- **WHEN** a completeness score of 0.25 is displayed
- **THEN** the score text is rendered in red color

---

### Requirement: Step indicator with status visualization
The phase progress SHALL be displayed as a horizontal step indicator with connecting lines and color-coded status dots, implemented via custom HTML and CSS.

Each step SHALL show one of four states:
- `waiting`: muted/gray, not yet started
- `running`: highlighted with primary color and a spinning animation
- `complete`: green with a checkmark icon
- `error`: red with an error indicator

The step indicator SHALL replace the current markdown-based strikethrough/bold simulation.

#### Scenario: All steps waiting at start
- **WHEN** no research has started yet
- **THEN** all four steps (decomposition, retrieval, critique, synthesis) are in the waiting state

#### Scenario: Steps progress sequentially
- **WHEN** a research task transitions from retrieval to critique phase
- **THEN** the decomposition and retrieval steps show as complete
- **AND** the critique step shows as active/running
- **AND** the synthesis step shows as waiting
