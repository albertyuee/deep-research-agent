"""Thread worker for async research streaming.

Runs the SSE connection in a background thread so the Streamlit
main thread stays responsive for UI interactions (e.g. stop button).
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading

import httpx

BACKEND_URL = "http://localhost:8000"


def run_research_worker(
    query: str,
    event_queue: queue.Queue,
    cancel_event: threading.Event,
):
    """Entry point for the worker thread.

    Args:
        query: Research query string.
        event_queue: Queue to push parsed SSE events to the main thread.
        cancel_event: Set by main thread to request cancellation.
    """
    asyncio.run(_async_worker(query, event_queue, cancel_event))


async def _async_worker(
    query: str,
    event_queue: queue.Queue,
    cancel_event: threading.Event,
):
    """Connect to backend, stream SSE events into the queue."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        # 1. Submit research task
        try:
            resp = await client.post(
                f"{BACKEND_URL}/api/v1/research",
                json={"query": query},
            )
        except Exception as e:
            event_queue.put(_evt("backend_error", {"message": f"无法连接后端: {e}"}))
            event_queue.put(_evt("done", {}))
            return

        if resp.status_code != 200:
            event_queue.put(_evt("backend_error", {"message": f"提交失败: {resp.text}"}))
            event_queue.put(_evt("done", {}))
            return

        task_data = resp.json()
        task_id = task_data["data"]["task_id"]
        event_queue.put(_evt("_task_id", {"task_id": task_id}))

        # 2. Stream SSE events
        url = f"{BACKEND_URL}/api/v1/research/{task_id}/stream"

        try:
            async with client.stream(
                "GET", url, timeout=httpx.Timeout(600, connect=30)
            ) as stream:
                async for line in stream.aiter_lines():
                    # Check for cancel request from main thread
                    if cancel_event.is_set():
                        try:
                            await client.post(
                                f"{BACKEND_URL}/api/v1/research/{task_id}/cancel"
                            )
                        except Exception:
                            pass
                        event_queue.put(
                            _evt("cancelled", {"message": "研究已被用户取消"})
                        )
                        event_queue.put(_evt("done", {}))
                        return

                    if not line.startswith("data: "):
                        continue

                    try:
                        event = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    event_queue.put(event)

                    if event.get("event") == "done":
                        return

        except asyncio.TimeoutError:
            event_queue.put(_evt("backend_error", {"message": "研究超时（600 秒）"}))
            event_queue.put(_evt("done", {}))
        except httpx.ReadTimeout:
            event_queue.put(_evt("backend_error", {"message": "SSE 连接读取超时"}))
            event_queue.put(_evt("done", {}))
        except httpx.ConnectTimeout:
            event_queue.put(_evt("backend_error", {"message": "SSE 连接超时"}))
            event_queue.put(_evt("done", {}))
        except Exception as e:
            err_msg = str(e) or type(e).__name__
            event_queue.put(
                _evt("backend_error", {"message": f"SSE 连接中断: {err_msg}"})
            )
            event_queue.put(_evt("done", {}))


def _evt(event_type: str, data: dict) -> dict:
    """Build a minimal event dict matching the SSE wire format."""
    return {"event": event_type, "data": data}
