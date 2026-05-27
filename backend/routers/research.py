"""Research API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.services.research_service import TaskStatus, task_manager
from research_agent.streaming import event_bus
from research_agent.graph import build_graph

router = APIRouter(prefix="/research", tags=["research"])

# Build the agent graph at module load
agent_graph = build_graph()


class ResearchRequest(BaseModel):
    query: str
    enable_web_search: bool = False


class ResearchResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


@router.post("", response_model=ResearchResponse)
async def submit_research(req: ResearchRequest):
    """Submit a new research task."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    task_id = event_bus.create_task()

    task_manager.create_task(task_id, req.query)
    task_manager.update_status(task_id, TaskStatus.RUNNING)

    # Run agent in background
    asyncio.create_task(_run_agent(task_id, req.query, req.enable_web_search))

    import sys
    web_flag = "ON" if req.enable_web_search else "OFF"
    print(f"[ROUTER] Task {task_id} submitted, query={req.query[:60]}, web={web_flag}",
          flush=True, file=sys.stderr)

    return ResearchResponse(
        success=True,
        data={"task_id": task_id},
    )


@router.get("/{task_id}/stream")
async def stream_research(task_id: str):
    """Subscribe to SSE stream for a research task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return StreamingResponse(
        event_bus.subscribe(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{task_id}", response_model=ResearchResponse)
async def get_research_status(task_id: str):
    """Get the status and result of a research task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return ResearchResponse(
        success=task.status == TaskStatus.COMPLETED,
        data={
            "task_id": task.task_id,
            "query": task.query,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
        },
    )


@router.post("/{task_id}/cancel", response_model=ResearchResponse)
async def cancel_research(task_id: str):
    """Cancel a running research task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.RUNNING:
        raise HTTPException(status_code=409, detail=f"Task is not running (current status: {task.status.value})")

    cancelled = task_manager.cancel_task(task_id)
    if cancelled:
        return ResearchResponse(
            success=True,
            data={"task_id": task_id, "message": "Task cancellation requested"},
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to cancel task")


async def _run_agent(task_id: str, query: str, enable_web_search: bool = False):
    """Execute the agent graph for a research task."""
    import sys, time
    current_task = asyncio.current_task()
    if current_task:
        task_manager.register_task(task_id, current_task)

    try:
        print(f"[AGENT {task_id}] _run_agent START, query={query[:60]}, web={enable_web_search}",
              flush=True, file=sys.stderr)
        initial_state = {
            "query": query,
            "task_id": task_id,
            "enable_web_search": enable_web_search,
        }
        t0 = time.time()
        print(f"[AGENT {task_id}] Calling agent_graph.ainvoke...", flush=True, file=sys.stderr)
        run_config = {
            "run_name": "deep_research_agent",
            "tags": ["deep-research", "langgraph"],
            "metadata": {
                "task_id": task_id,
                "query": query[:500],
                "enable_web_search": enable_web_search,
            },
        }
        result = await agent_graph.ainvoke(initial_state, config=run_config)
        print(f"[AGENT {task_id}] ainvoke DONE after {time.time()-t0:.1f}s", flush=True, file=sys.stderr)

        final_report = result.get("final_report", "")
        raw_sources = result.get("sources", [])
        task_manager.set_result(task_id, {
            "report": final_report,
            "sub_queries": result.get("sub_queries", []),
            "sources": raw_sources,
            "low_confidence_steps": result.get("low_confidence_steps", []),
        })
        task_manager.update_status(task_id, TaskStatus.COMPLETED)

    except asyncio.CancelledError:
        print(f"[AGENT {task_id}] Cancelled by user", flush=True, file=sys.stderr)
        event_bus.emit(task_id, "cancelled", {"message": "研究已被用户取消"})
        task_manager.update_status(task_id, TaskStatus.CANCELLED)
    except Exception as e:
        task_manager.update_status(task_id, TaskStatus.FAILED, error=str(e))
        event_bus.emit(task_id, "done", {"error": str(e)})
    finally:
        task_manager.unregister_task(task_id)
        event_bus.cleanup(task_id)
