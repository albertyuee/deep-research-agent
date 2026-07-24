"""FastAPI application entry point for Deep Research Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager

from config.settings import load_env

load_env()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.research import router as research_router
from backend.routers.quick_search import router as quick_search_router
from backend.routers.documents import router as documents_router
from backend.routers.settings import router as settings_router
from backend.routers.auth import router as auth_router
from backend.auth import init_auth_db
from research_agent.tools.mcp_client import mcp_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect MCP client. Shutdown: disconnect."""
    init_auth_db()
    await mcp_client.connect()
    yield
    await mcp_client.disconnect()


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
app.include_router(documents_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
