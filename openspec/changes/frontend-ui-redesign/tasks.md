## 1. Custom CSS Styling

- [x] 1.1 Create `frontend/static/style.css` with card container styles (white background, border-radius 12px, box-shadow, padding)
- [x] 1.2 Add score color coding CSS classes: `.score-pass` (green), `.score-fail` (red), `.score-warn` (orange)
- [x] 1.3 Add step indicator CSS (`.stepper`, `.stepper-step`, `.stepper-connector`, status dot colors)
- [x] 1.4 Add example query chip styles (`.query-chip`: border-radius 20px, hover effect)
- [x] 1.5 Add section spacing and typography adjustments
- [x] 1.6 Inject CSS into `app.py` via `st.markdown("<style>...</style>", unsafe_allow_html=True)` at startup

## 2. Empty State Guide Page

- [x] 2.1 Create `frontend/components/empty_state.py` with `render_empty_state()` function
- [x] 2.2 Implement welcome message and application description in the empty state
- [x] 2.3 Implement 3-step usage flow visualization using columns and icons
- [x] 2.4 Wire `render_empty_state()` into `app.py` right panel when `not is_running and not report`

## 3. Step Indicator Component

- [x] 3.1 Add `phase_states` dict to `AgentProgressDisplay._init_session_state()` tracking each phase's state (waiting/running/complete/error)
- [x] 3.2 Update phase state transitions in `handle_event()` handlers (e.g., plan_start → decomposition=running, plan_chunk → decomposition=complete + retrieval=running)
- [x] 3.3 Implement `_render_stepper()` function using custom HTML/CSS columns with status dots and connecting lines
- [x] 3.4 Replace the old markdown-based phase timeline in `render_progress_panel()` with `_render_stepper()`

## 4. Sidebar Reorganization

- [x] 4.1 Move `_render_event_log()` call from `render_progress_panel()` to `st.sidebar` block in `app.py`
- [x] 4.2 Move `_render_timing_stats()` call from `render_progress_panel()` to `st.sidebar` block in `app.py`
- [x] 4.3 Move `_render_retry_history()` call from `render_progress_panel()` to `st.sidebar` block in `app.py`
- [x] 4.4 Add sidebar hint text when no research task is active
- [x] 4.5 Verify all sidebar content is wrapped in containers for proper rendering during streaming

## 5. Score Color Coding

- [x] 5.1 Add `_color_class(score)` helper function returning CSS class name based on score thresholds (>=0.7 green, >=0.4 orange, <0.4 red)
- [x] 5.2 Apply color coding to critique scores in `render_progress_panel()` using `st.markdown` with inline HTML spans
- [x] 5.3 Apply color coding to retrieval top scores
- [x] 5.4 Apply color coding to individual relevance and completeness scores

## 6. Example Query Chips

- [x] 6.1 Define a list of 4-5 example research queries in `app.py` covering different domains
- [x] 6.2 Render chips as small `st.button` elements in a horizontal layout below the text input area
- [x] 6.3 Implement chip click handler that sets `st.session_state.query_preset` and triggers `st.rerun()`
- [x] 6.4 Wire `query_preset` into the text area's value prop so chip-selected text appears in the input

## 7. Form Input with Enter Support

- [x] 7.1 Wrap text area and submit button in `st.form` component
- [x] 7.2 Keep example query chips outside the form (to avoid double-submit issues)
- [x] 7.3 Handle form submission callback to start research
- [x] 7.4 Ensure form is disabled while `is_running` is True

## 8. Real Progress Data

- [x] 8.1 Add `progress` field reading in `AgentProgressDisplay.handle_event()` — store to `st.session_state.progress_value`
- [x] 8.2 Implement fallback progress estimation when `progress` field is absent from events
- [x] 8.3 Replace hardcoded progress values in `render_progress_panel()` with `st.session_state.progress_value`
- [x] 8.4 Force progress to 1.0 on `done` event
- [x] 8.5 Add `progress` field to backend SSE events in `backend/services/research_service.py` at each phase milestone

## 9. Integration & Polish

- [x] 9.1 Wire all components together in `app.py` and verify correct rendering order
- [x] 9.2 Remove or comment out old markdown phase timeline code
- [x] 9.3 Ensure left panel `[1, 2]` column ratio remains unchanged
- [x] 9.4 Manual end-to-end test: load page, verify empty state appears, click chip, submit, verify stepper advances, check sidebar logs populate
- [x] 9.5 Verify all error states: backend unreachable, timeout, SSE disconnect — all still show appropriate error messages
