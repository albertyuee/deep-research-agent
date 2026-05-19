"""Settings management API — read, update, hot-reload configuration."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
import re

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


def _get_milvus_settings() -> dict:
    return {
        "uri": app_settings.milvus.uri,
        "token": _mask_key(app_settings.milvus.token) if app_settings.milvus.token else "",
        "host": app_settings.milvus.host,
        "port": app_settings.milvus.port,
        "collection_name": app_settings.milvus.collection_name,
    }


def _write_env(updates: dict[str, str]) -> None:
    """Write key-value pairs to the .env file, preserving comments and structure."""
    # Read the original file as text (don't parse with dotenv_values — fragile)
    if ENV_FILE.exists():
        original_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    else:
        original_lines = []

    # Build a set of keys we're updating
    updated_keys = set()

    # Process each line: update matching keys, keep everything else intact
    result: list[str] = []
    for line in original_lines:
        stripped = line.strip()
        # Preserve empty lines and comments
        if not stripped or stripped.startswith("#"):
            result.append(line)
            continue

        # Parse KEY=VALUE
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", stripped)
        if match:
            key = match.group(1)
            if key in updates:
                result.append(f"{key}={updates[key]}")
                updated_keys.add(key)
            else:
                result.append(line)
        else:
            result.append(line)

    # Append any new keys that weren't in the original file
    for key, value in updates.items():
        if key not in updated_keys:
            result.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(result) + "\n", encoding="utf-8")


@router.get("")
async def get_settings():
    return {
        "success": True,
        "data": {
            "llm": _get_llm_settings(),
            "embedding": _get_embedding_settings(),
            "retrieval": _get_retrieval_settings(),
            "milvus": _get_milvus_settings(),
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
        "milvus.uri": ("MILVUS_URI", str),
        "milvus.token": ("MILVUS_TOKEN", str),
        "milvus.host": ("MILVUS_HOST", str),
        "milvus.port": ("MILVUS_PORT", str),
    }

    for section in ["llm", "embedding", "retrieval", "milvus"]:
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
    from research_agent.retrieval.vector_store import create_vector_store

    backend = app_settings.retrieval.vector_backend
    try:
        vs = create_vector_store()
        chunk_count = vs.count
    except Exception:
        chunk_count = 0

    return {
        "success": True,
        "data": {
            "vector_backend": backend,
            "chunk_count": chunk_count,
            "version": "0.1.0",
        },
    }
