# Fix Frontend Issues from Code Review

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the critical race condition in SSE event handling, stepper visual bug, event log memory leak, and remove dead code from the Streamlit frontend.

**Architecture:** The core fix consolidates "done" event handling into `_drain_event_queue()` so it is no longer consumed before `_finalise_on_done()` can process it. `_finalise_on_done()` is simplified to only serve as a thread-death safety net. Secondary fixes address step indicator timing, event log growth, and dead code removal.

**Tech Stack:** Python 3.12, Streamlit, httpx

---

### Task 1: Fix the "done" event race condition

**Files:**
- Modify: `frontend/app.py:89-191`

**Context:** Every polling cycle, `_drain_event_queue()` drains ALL events from the queue including `done` (which it discards via `pass`). Then `_finalise_on_done()` tries to find `done` in the same queue — but it's already gone. The report finalization only happens via the thread-is-alive fallback, causing a delay and fragile behavior.

- [ ] **Step 1: Handle "done" event directly in `_drain_event_queue()`**

Replace the `pass` on line 127 with the finalization logic:

```python
# In _drain_event_queue(), replace lines 125-127:
# OLD:
            elif event_type == "done":
                pass  # handled after draining

# NEW:
            elif event_type == "done":
                st.session_state["is_running"] = False
                streaming = st.session_state.get("_streaming_report", "")
                if streaming:
                    st.session_state["report"] = streaming
                st.session_state["_streaming_report"] = ""
                task_id = st.session_state.get("_task_id")
                if task_id:
                    _fetch_final_result(task_id, streaming)
```

- [ ] **Step 2: Simplify `_finalise_on_done()` to thread-death fallback only**

Replace the entire function body (lines 141-190) — remove the queue draining and done-seeking logic, keep only the thread-is-alive safety net:

```python
def _finalise_on_done():
    """Check if worker thread has died unexpectedly and finalise state."""
    worker = st.session_state.get("worker_thread")
    if worker is not None and not worker.is_alive():
        st.session_state["is_running"] = False
        streaming = st.session_state.get("_streaming_report", "")
        if streaming and not st.session_state["report"]:
            st.session_state["report"] = streaming
        st.session_state["_streaming_report"] = ""
        st.session_state["worker_thread"] = None
```

- [ ] **Step 3: Verify the fix**

Start the backend and frontend, submit a research query, and confirm:
1. The report appears promptly when the "done" event fires (not delayed until thread exit)
2. Sources are fetched and displayed
3. The stop button still works correctly
4. Cancelled research still preserves partial results

Run: Start backend with `uvicorn backend.main:app --reload` and frontend with `streamlit run frontend/app.py`

- [ ] **Step 4: Commit**

```bash
git add frontend/app.py
git commit -m "fix: handle done event in drain queue to fix race condition

The done SSE event was consumed by _drain_event_queue() but only
finalized in _finalise_on_done(), which runs after the queue is
already empty. Move finalization into _drain_event_queue() directly.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Fix stepper incorrectly showing retrieval as running during decomposition

**Files:**
- Modify: `frontend/components/agent_progress.py:114-127`

**Context:** `_on_plan_chunk()` sets `phases["retrieval"] = "running"` on every plan chunk, causing the step indicator to show "检索" as active while decomposition is still emitting chunks. The `retrieval_start` handler already sets this correctly when retrieval actually begins.

- [ ] **Step 1: Remove the premature retrieval phase activation**

In `_on_plan_chunk()`, remove lines 123-127 (the phase transition block):

```python
# In _on_plan_chunk(), replace lines 114-127:
# OLD:
    def _on_plan_chunk(self, data: dict) -> None:
        st.session_state["research_plan"].append({
            "index": data.get("index", 0),
            "question": data.get("question", ""),
            "strategy": data.get("strategy", ""),
            "rationale": data.get("rationale", ""),
        })
        if "decomposition" in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop("decomposition")
            st.session_state.get("phase_durations", {})["disassembly"] = time.time() - start
        # Transition: decomposition complete, retrieval next
        phases = st.session_state.get("phase_states", {})
        phases["decomposition"] = "complete"
        phases["retrieval"] = "running"

# NEW:
    def _on_plan_chunk(self, data: dict) -> None:
        st.session_state["research_plan"].append({
            "index": data.get("index", 0),
            "question": data.get("question", ""),
            "strategy": data.get("strategy", ""),
            "rationale": data.get("rationale", ""),
        })
        # Record decomposition duration on first chunk
        if "decomposition" in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop("decomposition")
            st.session_state.get("phase_durations", {})["disassembly"] = time.time() - start
            # Mark decomposition complete
            phases = st.session_state.get("phase_states", {})
            phases["decomposition"] = "complete"
```

The retrieval phase transition is already handled by `_on_retrieval_start()` on line 147: `phases["retrieval"] = "running"`.

- [ ] **Step 2: Verify the stepper behavior**

Run the app, submit a query, and watch the stepper:
1. Decomposition should show as "running" (pulsing dot) while plan chunks arrive
2. Retrieval should stay "waiting" until `retrieval_start` fires
3. All other transitions should be unchanged

- [ ] **Step 3: Commit**

```bash
git add frontend/components/agent_progress.py
git commit -m "fix: prevent stepper from showing retrieval as active during decomposition

_on_plan_chunk() was prematurely setting the retrieval phase to
'running' before retrieval actually started. The retrieval_start
handler already manages this transition correctly.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Cap event log size to prevent memory leak

**Files:**
- Modify: `frontend/components/agent_progress.py:88-93`

**Context:** Every SSE event is unconditionally appended to `st.session_state["event_log"]`. For long-running research tasks, this list grows without bound, consuming Streamlit session memory. Only the last 50 entries are displayed in the UI.

- [ ] **Step 1: Truncate event log after append**

In `handle_event()`, add truncation after the append on line 88-93:

```python
# In handle_event(), replace lines 88-93:
# OLD:
        summary = _summarize_event(event_type, data)
        st.session_state["event_log"].append({
            "elapsed": elapsed,
            "event_type": event_type,
            "summary": summary,
            "data": data,
        })

# NEW:
        summary = _summarize_event(event_type, data)
        st.session_state["event_log"].append({
            "elapsed": elapsed,
            "event_type": event_type,
            "summary": summary,
            "data": data,
        })
        # Keep only recent events to bound memory
        max_log = 500
        if len(st.session_state["event_log"]) > max_log:
            st.session_state["event_log"] = st.session_state["event_log"][-max_log:]
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/agent_progress.py
git commit -m "fix: cap event log at 500 entries to prevent memory leak

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Remove dead code

**Files:**
- Modify: `frontend/components/report_view.py:8-15`
- Modify: `frontend/app.py:18`

**Context:** `render_report()` in report_view.py is defined but never called — `app.py` renders reports inline with `st.markdown(report)`. The import at line 18 in app.py is also unused.

- [ ] **Step 1: Remove `render_report()` function**

Remove lines 8-15 from `frontend/components/report_view.py`:

```python
# REMOVE these lines:
def render_report(report: str):
    """Render the final research report in markdown."""
    if not report:
        return

    st.markdown("---")
    st.markdown("## 📄 研究报告")
    st.markdown(report)
```

- [ ] **Step 2: Remove unused import in app.py**

Remove the unreferenced import on line 18 (if present). Check the current imports — `render_report` is not imported, so this is actually already clean. Just verify:

```bash
grep -n "render_report" frontend/app.py
```

Expected: no matches (already not imported).

- [ ] **Step 3: Commit**

```bash
git add frontend/components/report_view.py
git commit -m "chore: remove unused render_report function

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Add `current_detail` to session state defaults

**Files:**
- Modify: `frontend/app.py:45-66`

**Context:** `current_detail` is set during form submission (line 287) but not included in the `_defaults` initialization dict. Other keys like `progress_value` and `research_plan` are in both `_defaults` and `AgentProgressDisplay._init_session_state()`, causing duplication and confusion about ownership.

- [ ] **Step 1: Add `current_detail` to `_defaults`**

In `_defaults` dict (lines 45-66), add the missing key:

```python
# Add after line 61:
    "current_detail": "",
```

Full context for the edit — insert between existing lines:
```python
    "progress_value": 0.0,
    "current_detail": "",       # <-- add this line
    "_chip_query": "",
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app.py
git commit -m "fix: add current_detail to session state defaults

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Cache CSS file reading to avoid re-reading every poll cycle

**Files:**
- Modify: `frontend/app.py:31-33`

**Context:** During the polling loop (every ~150ms when running), the CSS file is re-read from disk on every `st.rerun()`. This is unnecessary I/O.

- [ ] **Step 1: Cache the CSS string with `@st.cache_resource`**

Replace lines 31-33:

```python
# OLD:
_css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
with open(_css_path, "r", encoding="utf-8") as _f:
    st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# NEW:
@st.cache_resource
def _load_css() -> str:
    css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        return f.read()

st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)
```

Also remove the now-unused `_css_path` variable and the `os` import if no longer needed (check: `os.path.dirname` is still used in `_load_css`, so keep `import os`).

- [ ] **Step 2: Verify CSS still loads correctly**

Run the app, confirm styling is identical on both idle and running states.

- [ ] **Step 3: Commit**

```bash
git add frontend/app.py
git commit -m "perf: cache CSS file loading with st.cache_resource

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage:** All issues from the code review are addressed:
- Critical race condition → Task 1
- Stepper visual bug → Task 2
- Event log memory leak → Task 3
- Dead code (render_report) → Task 4
- Missing current_detail default → Task 5
- CSS re-read optimization → Task 6

**2. Placeholder scan:** No TBD, TODO, or "add error handling" patterns found. All code changes are shown verbatim.

**3. Type consistency:** No cross-task type dependencies — each task is self-contained and modifies independent sections of the code.
