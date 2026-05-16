"""Settings management API — read, update, hot-reload configuration."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv, dotenv_values

from config.settings import reload_settings
from config.settings import settings as app_settings

router = APIRouter(prefix="/settings", tags=["settings"])

ENV_FILE = Path(__file__).parent.parent.parent / "config" / ".env"


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return ""
    return key[:3] + "***" + key[-4:]


def _get_llm_settings() -> dict:
    return {
        "provider": app_settings.llm.provider,
        "model": app_settings.llm.model,
        "api_key": _mask_key(app_settings.llm.api_key),
        "base_url": app_settings.llm.base_url,
        "temperature": app_settings.llm.temperature,
        "max_tokens": app_settings.llm.max_tokens,
    }


def _get_embedding_settings() -> dict:
    return {
        "mode": app_settings.embedding.mode,
        "model": app_settings.embedding.model,
        "device": app_settings.embedding.device,
        "api_base_url": app_settings.embedding.api_base_url,
        "api_key": _mask_key(app_settings.embedding.api_key),
    }


def _get_retrieval_settings() -> dict:
    return {
        "top_k": app_settings.retrieval.top_k,
        "max_retries": app_settings.retrieval.max_retries,
        "critique_threshold": app_settings.retrieval.critique_threshold,
        "rrf_k": app_settings.retrieval.rrf_k,
        "vector_backend": app_settings.retrieval.vector_backend,
    }


def _write_env(updates: dict[str, str]) -> None:
    """Write key-value pairs to the .env file, preserving existing keys."""
    load_dotenv(ENV_FILE)
    current = dict(dotenv_values(ENV_FILE))
    current.update(updates)

    lines = []
    for k, v in current.items():
        lines.append(f"{k}={v}")

    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")


@router.get("")
async def get_settings():
    return {
        "success": True,
        "data": {
            "llm": _get_llm_settings(),
            "embedding": _get_embedding_settings(),
            "retrieval": _get_retrieval_settings(),
        },
    }


@router.patch("")
async def update_settings(body: dict):
    """Partially update settings. Writes to .env and hot-reloads."""
    env_updates: dict[str, str] = {}
    updated_keys: list[str] = []

    path_map = {
        "llm.provider": ("LLM_PROVIDER", str),
        "llm.model": ("LLM_MODEL", str),
        "llm.api_key": ("LLM_API_KEY", str),
        "llm.base_url": ("LLM_BASE_URL", str),
        "llm.temperature": ("LLM_TEMPERATURE", str),
        "llm.max_tokens": ("LLM_MAX_TOKENS", str),
        "embedding.mode": ("EMBEDDING_MODE", str),
        "embedding.model": ("EMBEDDING_MODEL", str),
        "embedding.device": ("EMBEDDING_DEVICE", str),
        "embedding.api_base_url": ("EMBEDDING_API_BASE_URL", str),
        "embedding.api_key": ("EMBEDDING_API_KEY", str),
        "retrieval.top_k": ("RETRIEVAL_TOP_K", str),
        "retrieval.max_retries": ("RETRIEVAL_MAX_RETRIES", str),
        "retrieval.critique_threshold": ("RETRIEVAL_CRITIQUE_THRESHOLD", str),
        "retrieval.rrf_k": ("RETRIEVAL_RRF_K", str),
        "retrieval.vector_backend": ("RETRIEVAL_VECTOR_BACKEND", str),
    }

    for section in ["llm", "embedding", "retrieval"]:
        if section in body:
            for key, value in body[section].items():
                path = f"{section}.{key}"
                if path in path_map:
                    env_key, _ = path_map[path]
                    if "api_key" in key and value and "***" in str(value):
                        continue
                    env_updates[env_key] = str(value)
                    updated_keys.append(path)

    if not env_updates:
        raise HTTPException(status_code=400, detail="No valid settings to update")

    _write_env(env_updates)
    reload_settings()

    return {
        "success": True,
        "data": {
            "updated": updated_keys,
            "need_restart": False,
        },
    }


@router.get("/system-info")
async def get_system_info():
    try:
        from research_agent.retrieval.vector_store import VectorStore
        vs = VectorStore()
        chroma_chunks = vs.count
    except Exception:
        chroma_chunks = 0

    return {
        "success": True,
        "data": {
            "chroma_chunks": chroma_chunks,
            "version": "0.1.0",
        },
    }
