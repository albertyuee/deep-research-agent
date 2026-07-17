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
        "dimension": app_settings.embedding.dimension,
        "query_max_chars": app_settings.embedding.query_max_chars,
        "api_base_url": app_settings.embedding.api_base_url,
        "api_key": _mask_key(app_settings.embedding.api_key),
    }


def _get_retrieval_settings() -> dict:
    return {
        "top_k": app_settings.retrieval.top_k,
        "retry_top_k_multiplier": app_settings.retrieval.retry_top_k_multiplier,
        "max_top_k": app_settings.retrieval.max_top_k,
        "max_concurrency": app_settings.retrieval.max_concurrency,
        "max_retries": app_settings.retrieval.max_retries,
        "critique_threshold": app_settings.retrieval.critique_threshold,
        "rrf_k": app_settings.retrieval.rrf_k,
        "vector_backend": app_settings.retrieval.vector_backend,
    }


def _get_reasoning_settings() -> dict:
    return {
        "enabled": app_settings.reasoning.enabled,
        "max_sub_queries": app_settings.reasoning.max_sub_queries,
        "max_hops": app_settings.reasoning.max_hops,
        "context_max_chars": app_settings.reasoning.context_max_chars,
        "search_query_max_chars": app_settings.reasoning.search_query_max_chars,
    }


def _get_rerank_settings() -> dict:
    return {
        "enabled": app_settings.rerank.enabled,
        "provider": app_settings.rerank.provider,
        "model": app_settings.rerank.model,
        "api_key": _mask_key(app_settings.rerank.api_key) if app_settings.rerank.api_key else "",
        "base_url": app_settings.rerank.base_url,
        "top_n": app_settings.rerank.top_n,
        "candidate_multiplier": app_settings.rerank.candidate_multiplier,
        "timeout": app_settings.rerank.timeout,
        "instruction": app_settings.rerank.instruction,
    }


def _get_mcp_settings() -> dict:
    return {
        "web_search_enabled": app_settings.mcp.web_search_enabled,
        "tavily_api_key": _mask_key(app_settings.mcp.tavily_api_key) if app_settings.mcp.tavily_api_key else "",
        "tavily_max_results": app_settings.mcp.tavily_max_results,
        "web_search_timeout": app_settings.mcp.web_search_timeout,
    }


def _get_milvus_settings() -> dict:
    return {
        "uri": app_settings.milvus.uri,
        "token": _mask_key(app_settings.milvus.token) if app_settings.milvus.token else "",
        "host": app_settings.milvus.host,
        "port": app_settings.milvus.port,
        "collection_name": app_settings.milvus.collection_name,
    }


def _get_langsmith_settings() -> dict:
    tracing_v2 = app_settings.langsmith.tracing_v2 or app_settings.langsmith.tracing
    return {
        "tracing": app_settings.langsmith.tracing,
        "tracing_v2": tracing_v2,
        "api_key": _mask_key(app_settings.langsmith.api_key) if app_settings.langsmith.api_key else "",
        "project": app_settings.langsmith.project,
        "endpoint": app_settings.langsmith.endpoint,
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
            "reasoning": _get_reasoning_settings(),
            "rerank": _get_rerank_settings(),
            "milvus": _get_milvus_settings(),
            "mcp": _get_mcp_settings(),
            "langsmith": _get_langsmith_settings(),
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
        "embedding.query_max_chars": ("EMBEDDING_QUERY_MAX_CHARS", str),
        "retrieval.top_k": ("RETRIEVAL_TOP_K", str),
        "retrieval.retry_top_k_multiplier": ("RETRIEVAL_RETRY_TOP_K_MULTIPLIER", str),
        "retrieval.max_top_k": ("RETRIEVAL_MAX_TOP_K", str),
        "retrieval.max_concurrency": ("RETRIEVAL_MAX_CONCURRENCY", str),
        "retrieval.max_retries": ("RETRIEVAL_MAX_RETRIES", str),
        "retrieval.critique_threshold": ("RETRIEVAL_CRITIQUE_THRESHOLD", str),
        "retrieval.rrf_k": ("RETRIEVAL_RRF_K", str),
        "retrieval.vector_backend": ("RETRIEVAL_VECTOR_BACKEND", str),
        "reasoning.enabled": ("REASONING_ENABLED", lambda v: str(v).lower()),
        "reasoning.max_sub_queries": ("REASONING_MAX_SUB_QUERIES", str),
        "reasoning.max_hops": ("REASONING_MAX_HOPS", str),
        "reasoning.context_max_chars": ("REASONING_CONTEXT_MAX_CHARS", str),
        "reasoning.search_query_max_chars": ("REASONING_SEARCH_QUERY_MAX_CHARS", str),
        "rerank.enabled": ("RERANK_ENABLED", lambda v: str(v).lower()),
        "rerank.provider": ("RERANK_PROVIDER", str),
        "rerank.model": ("RERANK_MODEL", str),
        "rerank.api_key": ("RERANK_API_KEY", str),
        "rerank.base_url": ("RERANK_BASE_URL", str),
        "rerank.top_n": ("RERANK_TOP_N", str),
        "rerank.candidate_multiplier": ("RERANK_CANDIDATE_MULTIPLIER", str),
        "rerank.timeout": ("RERANK_TIMEOUT", str),
        "rerank.instruction": ("RERANK_INSTRUCTION", str),
        "milvus.uri": ("MILVUS_URI", str),
        "milvus.token": ("MILVUS_TOKEN", str),
        "milvus.host": ("MILVUS_HOST", str),
        "milvus.port": ("MILVUS_PORT", str),
        "milvus.collection_name": ("MILVUS_COLLECTION_NAME", str),
        "mcp.web_search_enabled": ("MCP_WEB_SEARCH_ENABLED", lambda v: str(v).lower()),
        "mcp.tavily_api_key": ("MCP_TAVILY_API_KEY", str),
        "mcp.tavily_max_results": ("MCP_TAVILY_MAX_RESULTS", str),
        "mcp.web_search_timeout": ("MCP_WEB_SEARCH_TIMEOUT", str),
        "langsmith.tracing": ("LANGSMITH_TRACING", lambda v: str(v).lower()),
        "langsmith.tracing_v2": ("LANGSMITH_TRACING_V2", lambda v: str(v).lower()),
        "langsmith.api_key": ("LANGSMITH_API_KEY", str),
        "langsmith.project": ("LANGSMITH_PROJECT", str),
        "langsmith.endpoint": ("LANGSMITH_ENDPOINT", str),
    }

    for section in ["llm", "embedding", "retrieval", "reasoning", "rerank", "milvus", "mcp", "langsmith"]:
        if section in body:
            for key, value in body[section].items():
                path = f"{section}.{key}"
                if path in path_map:
                    env_key, converter = path_map[path]
                    if ("api_key" in key or key == "token") and value and "***" in str(value):
                        continue
                    converted = converter(value)
                    env_updates[env_key] = converted
                    if path == "langsmith.tracing":
                        env_updates["LANGSMITH_TRACING_V2"] = converted
                        env_updates["LANGCHAIN_TRACING_V2"] = converted
                    elif path == "langsmith.tracing_v2":
                        env_updates["LANGCHAIN_TRACING_V2"] = converted
                    elif path == "langsmith.api_key":
                        env_updates["LANGCHAIN_API_KEY"] = converted
                    elif path == "langsmith.project":
                        env_updates["LANGCHAIN_PROJECT"] = converted
                    elif path == "langsmith.endpoint":
                        env_updates["LANGCHAIN_ENDPOINT"] = converted
                    updated_keys.append(path)

    if not env_updates:
        raise HTTPException(status_code=400, detail="No valid settings to update")

    _write_env(env_updates)
    reload_settings()
    # Configuration objects and backend clients are cached in process. Reset
    # those caches so a hot reload actually affects the next request.
    from research_agent.retrieval.service import retrieval_service
    from research_agent.retrieval.embedding import reset_embedding_service
    retrieval_service.reset()
    reset_embedding_service()
    global app_settings
    from config.settings import settings as reloaded_settings
    app_settings = reloaded_settings

    return {
        "success": True,
        "data": {
            "updated": updated_keys,
            "need_restart": any(key.startswith("langsmith.") for key in updated_keys),
        },
    }


@router.post("/test-connection")
async def test_connection(body: dict):
    """Test connection for LLM, Embedding, or Milvus with current or provided config."""
    service = body.get("service", "")
    config = body.get("config", {})

    if service == "llm":
        return await _test_llm(config)
    elif service == "embedding":
        return await _test_embedding(config)
    elif service == "milvus":
        return await _test_milvus(config)
    elif service == "langsmith":
        return await _test_langsmith(config)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")


async def _test_llm(config: dict):
    """Test LLM connection with a simple chat completion."""
    from research_agent.llm.factory import create_llm_client

    try:
        # Temporarily override settings if config provided
        client = create_llm_client()
        messages = [{"role": "user", "content": "Hi"}]
        response = await client.chat(messages, temperature=0.0, max_tokens=32)
        return {
            "success": True,
            "data": {
                "message": "LLM 连接成功",
                "preview": response.strip()[:100],
            },
        }
    except Exception as e:
        return {
            "success": False,
            "data": {"message": f"LLM 连接失败: {e}"},
        }


async def _test_embedding(config: dict):
    """Test embedding service by embedding a short text."""
    from research_agent.retrieval.embedding import get_embedding_service

    try:
        emb_service = get_embedding_service()
        result = emb_service.embed_query("测试文本")
        dim = len(result) if hasattr(result, "__len__") else result.shape[0]
        return {
            "success": True,
            "data": {
                "message": f"嵌入模型连接成功，维度: {dim}",
            },
        }
    except Exception as e:
        return {
            "success": False,
            "data": {"message": f"嵌入模型连接失败: {e}"},
        }


async def _test_langsmith(config: dict):
    """Test LangSmith API key and project access."""
    try:
        from langsmith import Client

        raw_api_key = config.get("api_key")
        api_key = app_settings.langsmith.api_key if raw_api_key and "***" in str(raw_api_key) else raw_api_key or app_settings.langsmith.api_key
        endpoint = config.get("endpoint") or app_settings.langsmith.endpoint
        project = config.get("project") or app_settings.langsmith.project
        if not api_key:
            return {
                "success": False,
                "data": {"message": "LangSmith API Key 未配置"},
            }

        client = Client(api_key=api_key, api_url=endpoint)
        list(client.list_projects(limit=1))
        return {
            "success": True,
            "data": {
                "message": f"LangSmith 连接成功，项目: {project}",
            },
        }
    except Exception as e:
        return {
            "success": False,
            "data": {"message": f"LangSmith 连接失败: {e}"},
        }


async def _test_milvus(config: dict):
    """Test Milvus / Zilliz Cloud connection."""
    from research_agent.retrieval.vector_store import create_vector_store

    try:
        vs = create_vector_store()
        chunk_count = vs.count
        backend = app_settings.retrieval.vector_backend
        label = "Zilliz Cloud" if app_settings.milvus.uri else "自建 Milvus"
        return {
            "success": True,
            "data": {
                "message": f"{label} 连接成功，已索引 {chunk_count} 个文档",
            },
        }
    except Exception as e:
        return {
            "success": False,
            "data": {"message": f"向量存储连接失败: {e}"},
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
