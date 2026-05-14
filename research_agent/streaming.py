"""SSE event manager for real-time agent progress streaming."""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class AgentEvent:
    event_type: str
    data: dict
    task_id: str = ""


class EventBus:
    """In-memory event bus for agent progress streaming.

    Uses a list buffer + asyncio.Event for reliable event delivery,
    avoiding potential asyncio.Queue ordering issues under high concurrency.
    """

    def __init__(self):
        self._buffers: dict[str, list[AgentEvent]] = {}
        self._events: dict[str, asyncio.Event] = {}

    def create_task(self) -> str:
        task_id = uuid.uuid4().hex[:12]
        self._buffers[task_id] = []
        self._events[task_id] = asyncio.Event()
        print(f"[EVENTBUS] create_task: {task_id}", flush=True, file=sys.stderr)
        return task_id

    def emit(self, task_id: str, event_type: str, data: dict | None = None) -> None:
        buf = self._buffers.get(task_id)
        ev = self._events.get(task_id)
        if buf is not None:
            event = AgentEvent(event_type=event_type, data=data or {}, task_id=task_id)
            buf.append(event)
            if ev is not None:
                ev.set()
            print(f"[EVENTBUS] emit: {task_id[:6]}... {event_type}", flush=True, file=sys.stderr)
        else:
            print(f"[EVENTBUS] emit FAILED: task {task_id[:6]}... NOT FOUND (available: {list(self._buffers.keys())[:3]})", flush=True, file=sys.stderr)

    async def subscribe(self, task_id: str) -> AsyncIterator[str]:
        buf = self._buffers.get(task_id)
        ev = self._events.get(task_id)
        if buf is None or ev is None:
            print(f"[EVENTBUS] subscribe: task {task_id[:6]}... NOT FOUND", flush=True, file=sys.stderr)
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': 'Task not found'}})}\n\n"
            return

        print(f"[EVENTBUS] subscribe START: {task_id[:6]}... buf_size={len(buf)}", flush=True, file=sys.stderr)
        read_pos = 0
        idle_seconds = 0
        yielded = 0

        while True:
            # Check for new events
            while read_pos < len(buf):
                event = buf[read_pos]
                read_pos += 1
                idle_seconds = 0
                ev.clear()
                sse_data = json.dumps(
                    {"event": event.event_type, "data": event.data},
                    ensure_ascii=False,
                )
                yield f"data: {sse_data}\n\n"
                yielded += 1
                if event.event_type == "done":
                    print(f"[EVENTBUS] subscribe DONE: {task_id[:6]}... yielded={yielded}", flush=True, file=sys.stderr)
                    return

            # Wait for more events or timeout
            ev.clear()
            try:
                await asyncio.wait_for(ev.wait(), timeout=2)
            except asyncio.TimeoutError:
                idle_seconds += 2
                yield f"data: {json.dumps({'event': 'heartbeat', 'data': {'idle_seconds': idle_seconds}})}\n\n"
                if idle_seconds >= 600:
                    yield f"data: {json.dumps({'event': 'timeout', 'data': {}})}\n\n"
                    print(f"[EVENTBUS] subscribe TIMEOUT: {task_id[:6]}... yielded={yielded}", flush=True, file=sys.stderr)
                    return

    def cleanup(self, task_id: str) -> None:
        self._buffers.pop(task_id, None)
        self._events.pop(task_id, None)


# Global event bus instance
event_bus = EventBus()
