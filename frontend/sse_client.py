"""SSE client for connecting to the backend streaming API."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx


async def subscribe_to_task(base_url: str, task_id: str) -> AsyncIterator[dict]:
    """Subscribe to SSE events for a research task.

    Args:
        base_url: Backend base URL (e.g., http://localhost:8000).
        task_id: Research task ID.

    Yields:
        Parsed event dicts with 'event' and 'data' fields.
    """
    url = f"{base_url}/api/v1/research/{task_id}/stream"
    async with httpx.AsyncClient(timeout=httpx.Timeout(300)) as client:
        async with client.stream("GET", url) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    payload = line[6:]
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError:
                        continue
