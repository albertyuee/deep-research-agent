"""FastAPI application entry point for Deep Research Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.research import router as research_router
from backend.routers.quick_search import router as quick_search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    yield


app = FastAPI(
    title="Deep Research Agent",
    description="Agentic RAG — autonomous query decomposition, adaptive retrieval, quality critique, and report synthesis",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router, prefix="/api/v1")
app.include_router(quick_search_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
