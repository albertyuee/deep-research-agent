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


# Singleton
task_manager = ResearchTaskManager()
