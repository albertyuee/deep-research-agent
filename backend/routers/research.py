"""Research API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.services.research_service import TaskStatus, task_manager
from research_agent.streaming import event_bus
from research_agent.graph import build_graph
from research_agent.observability.timing import drain_task_timings
from research_agent.state import ResearchMode
from backend.auth import User, allowed_upload_ids, current_user
from backend.routers.documents import _read_files_meta

router = APIRouter(prefix="/research", tags=["research"])

# Build the agent graph at module load
agent_graph = build_graph()


class ResearchRequest(BaseModel):
    query: str
    enable_web_search: bool = False
    research_mode: ResearchMode = "auto"
    max_hops: int | None = Field(default=None, ge=1, le=8)


class ResearchResponse(BaseModel):
    success: bool
    data: dict
    error: str | None = None


@router.post("", response_model=ResearchResponse)
async def submit_research(req: ResearchRequest, user: User = Depends(current_user)):
    """Submit a new research task."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    task_id = event_bus.create_task()

    task_manager.create_task(task_id, req.query, owner_id=user.id)
    task_manager.update_status(task_id, TaskStatus.RUNNING)

    # Run agent in background
    asyncio.create_task(_run_agent(
        task_id,
        req.query,
        req.enable_web_search,
        req.research_mode,
        req.max_hops,
        allowed_upload_ids(user, _read_files_meta().get("files", [])),
    ))

    import sys
    web_flag = "ON" if req.enable_web_search else "OFF"
    print(f"[ROUTER] Task {task_id} submitted, query={req.query[:60]}, "
          f"web={web_flag}, mode={req.research_mode}, max_hops={req.max_hops}",
          flush=True, file=sys.stderr)

    return ResearchResponse(
        success=True,
        data={"task_id": task_id, "research_mode": req.research_mode},
    )


@router.get("/{task_id}/stream")
async def stream_research(task_id: str, user: User = Depends(current_user)):
    """Subscribe to SSE stream for a research task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not user.is_admin and task.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该研究任务")

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
async def get_research_status(task_id: str, user: User = Depends(current_user)):
    """Get the status and result of a research task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not user.is_admin and task.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该研究任务")

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
async def cancel_research(task_id: str, user: User = Depends(current_user)):
    """Cancel a running research task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not user.is_admin and task.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权取消该研究任务")

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


async def _run_agent(
    task_id: str,
    query: str,
    enable_web_search: bool = False,
    research_mode: ResearchMode = "auto",
    max_hops: int | None = None,
    allowed_ids: set[str] | None = None,
):
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
            "research_mode": research_mode,
            "allowed_upload_ids": allowed_ids,
        }
        if max_hops is not None:
            initial_state["max_hops"] = max_hops
        t0 = time.time()
        print(f"[AGENT {task_id}] Calling agent_graph.ainvoke...", flush=True, file=sys.stderr)
        run_config = {
            "run_name": "deep_research_agent",
            "tags": ["deep-research", "langgraph"],
            "metadata": {
                "task_id": task_id,
                "query": query[:500],
                "enable_web_search": enable_web_search,
                "research_mode": research_mode,
                "max_hops": max_hops,
            },
        }
        result = await agent_graph.ainvoke(initial_state, config=run_config)
        print(f"[AGENT {task_id}] ainvoke DONE after {time.time()-t0:.1f}s", flush=True, file=sys.stderr)

        final_report = result.get("final_report", "")
        raw_sources = result.get("sources", [])
        timings = drain_task_timings(task_id)
        task_manager.set_result(task_id, {
            "report": final_report,
            "sub_queries": result.get("sub_queries", []),
            "sources": raw_sources,
            "low_confidence_steps": result.get("low_confidence_steps", []),
            "hop_count": result.get("hop_count", 0),
            "reasoning_paths": result.get("reasoning_paths", []),
            "step_contexts": result.get("step_contexts", {}),
            "research_mode": result.get("research_mode", research_mode),
            "timings": timings,
        })
        task_manager.update_status(task_id, TaskStatus.COMPLETED)
        # Emit the terminal event only after the final result is queryable.
        # The frontend can now fetch report sources immediately without racing
        # task_manager.set_result().
        event_bus.emit(task_id, "done", {
            "report_length": len(final_report),
            "timing_count": len(timings),
            "progress": 1.0,
        })

    except asyncio.CancelledError:
        drain_task_timings(task_id)
        print(f"[AGENT {task_id}] Cancelled by user", flush=True, file=sys.stderr)
        event_bus.emit(task_id, "cancelled", {"message": "研究已被用户取消"})
        task_manager.update_status(task_id, TaskStatus.CANCELLED)
    except Exception as e:
        drain_task_timings(task_id)
        task_manager.update_status(task_id, TaskStatus.FAILED, error=str(e))
        event_bus.emit(task_id, "error", {"message": str(e)})
    finally:
        task_manager.unregister_task(task_id)
        event_bus.schedule_cleanup(task_id)
