## 1. Phase Timing Tracking

- [x] 1.1 Add phase timing state variables (`phase_start_times`, `phase_durations`) to `AgentProgressDisplay._init_session_state()`
- [x] 1.2 Record start timestamps for each phase in `handle_event()` when phase-start events arrive (decomposition, retrieval, critique, synthesis)
- [x] 1.3 Calculate and store phase durations when phase-end events arrive (critique_result for retrieval+c critique phases, done for synthesis)
- [x] 1.4 Implement `_render_timing_stats()` function that displays per-phase durations and total elapsed time in a collapsible expander

## 2. Event Log Panel

- [x] 2.1 Add event log state with timestamps in `AgentProgressDisplay` (store `(elapsed_seconds, event_type, data_summary)` tuples)
- [x] 2.2 Implement `_render_event_log()` function that renders a scrollable table of events with columns: time, event_type, key data summary
- [x] 2.3 Make each event row expandable to show the full raw payload data
- [x] 2.4 Default the event log panel to collapsed via `st.expander(expanded=False)`

## 3. Retry History Panel

- [x] 3.1 Store retry history details in `AgentProgressDisplay` — capture attempt count, critique score at retry, and retry suggestion from `retry_triggered` events
- [x] 3.2 Implement `_render_retry_history()` that shows retry attempts with reason and suggestion, only when retries occurred

## 4. Enhanced Step Details

- [x] 4.1 In `_on_retrieval_result()`, store a preview (first 200 chars) of the top result content to session state
- [x] 4.2 In `_on_critique_result()`, store the `reasoning` and `retry_suggestion` fields to session state
- [x] 4.3 Update the critique expander in `render_progress_panel()` to display reasoning text and retry suggestion for failed critiques
- [x] 4.4 Update the retrieval expander to show result content preview alongside scores

## 5. Integration & Polish

- [x] 5.1 Wire all new render functions (`_render_event_log`, `_render_timing_stats`, `_render_retry_history`) into `render_progress_panel()` at appropriate positions
- [x] 5.2 Verify all new sections default to collapsed state and do not disrupt the main progress view
- [x] 5.3 Manual end-to-end test: submit a research query, verify event log populates in real-time, timing stats appear, and step details show enhanced information
