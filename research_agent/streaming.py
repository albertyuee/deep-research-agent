"""SSE event manager for real-time agent progress streaming."""

from __future__ import annotations

import asyncio
import json
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

    Each research task gets its own asyncio.Queue for SSE delivery.
    """

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}

    def create_task(self) -> str:
        task_id = uuid.uuid4().hex[:12]
        self._queues[task_id] = asyncio.Queue()
        return task_id

    def emit(self, task_id: str, event_type: str, data: dict | None = None) -> None:
        queue = self._queues.get(task_id)
        if queue:
            event = AgentEvent(event_type=event_type, data=data or {}, task_id=task_id)
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def subscribe(self, task_id: str) -> AsyncIterator[str]:
        queue = self._queues.get(task_id)
        if not queue:
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': 'Task not found'}})}\n\n"
            return

        while True:
            try:
                event: AgentEvent = await asyncio.wait_for(queue.get(), timeout=300)
                sse_data = json.dumps({"event": event.event_type, "data": event.data}, ensure_ascii=False)
                yield f"data: {sse_data}\n\n"

                if event.event_type == "done":
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'event': 'timeout', 'data': {}})}\n\n"
                break

    def cleanup(self, task_id: str) -> None:
        self._queues.pop(task_id, None)


# Global event bus instance
event_bus = EventBus()
