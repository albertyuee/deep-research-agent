"""Task management service for research tasks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ResearchTask:
    task_id: str
    query: str
    status: TaskStatus = TaskStatus.PENDING
    result: dict | None = None
    error: str | None = None


class ResearchTaskManager:
    """In-memory task manager for research tasks."""

    def __init__(self):
        self._tasks: dict[str, ResearchTask] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}

    def create_task(self, task_id: str, query: str) -> ResearchTask:
        task = ResearchTask(task_id=task_id, query=query)
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> ResearchTask | None:
        return self._tasks.get(task_id)

    def update_status(self, task_id: str, status: TaskStatus, error: str | None = None):
        task = self._tasks.get(task_id)
        if task:
            task.status = status
            if error:
                task.error = error

    def set_result(self, task_id: str, result: dict):
        task = self._tasks.get(task_id)
        if task:
            task.result = result

    def register_task(self, task_id: str, asyncio_task: asyncio.Task):
        """Store reference to a running asyncio Task for potential cancellation."""
        self._running_tasks[task_id] = asyncio_task

    def unregister_task(self, task_id: str):
        """Remove asyncio Task reference after completion/cancellation."""
        self._running_tasks.pop(task_id, None)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running research task. Returns True if task was found and cancelled."""
        asyncio_task = self._running_tasks.get(task_id)
        if asyncio_task and not asyncio_task.done():
            asyncio_task.cancel()
            return True
        return False


# Singleton
task_manager = ResearchTaskManager()
