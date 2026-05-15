## 1. Fix SSE stream timeout handling

- [x] 1.1 Change AsyncClient default timeout from 10s to 30s
- [x] 1.2 Change SSE stream timeout from 300s to 600s with 30s connect
- [x] 1.3 Add separate `httpx.ReadTimeout` and `httpx.ConnectTimeout` exception handling
- [x] 1.4 Improve error message to include exception type when str(e) is empty

## 2. Fix Streamlit duplicate key errors

- [x] 2.1 Replace fixed `key="event_log_selector"` with dynamic `f"payload_{i}_{len(events)}"`
- [x] 2.2 Add unique keys to nested critique reasoning expanders
- [x] 2.3 Add unique keys to retrieval preview expanders
- [x] 2.4 Add try/except around `st.json()` calls

## 3. Fix duplicate research_plan_start trigger

- [x] 3.1 Remove manual `handle_event("research_plan_start")` call in app.py before SSE stream
- [x] 3.2 Let backend SSE event be the single source of truth for plan_start

## 4. Skip heartbeat in event log

- [x] 4.1 Add early return in `handle_event` when event_type is "heartbeat"
