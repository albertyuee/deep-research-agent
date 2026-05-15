## 1. Fix LangGraph conditional edge deadlock

- [x] 1.1 Move state mutation logic from `should_retry` to `critique_node`
- [x] 1.2 Simplify `should_retry` to pure routing function (read-only, returns "retrieval" or "synthesis")
- [x] 1.3 Add `_dbg()` debug helper to graph.py for tracing execution

## 2. Fix task_id missing from ResearchState

- [x] 2.1 Add `task_id: str` field to `ResearchState` TypedDict in state.py
- [x] 2.2 Verify LangGraph no longer strips task_id during ainvoke

## 3. Rewrite EventBus for reliable SSE delivery

- [x] 3.1 Replace `asyncio.Queue` with `list` buffer + `asyncio.Event` signaling
- [x] 3.2 Add heartbeat event every 2s to keep frontend timer alive
- [x] 3.3 Add debug logging to emit/subscribe/create_task methods
- [x] 3.4 Add 600s idle timeout with explicit timeout event

## 4. Backend debugging

- [x] 4.1 Add `[ROUTER]` log in submit_research
- [x] 4.2 Add `[AGENT]` log in _run_agent with timing
