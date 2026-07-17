#!/bin/bash

# Deep Research Agent 一键启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Deep Research Agent 启动脚本"
echo "=========================================="
echo ""

# 始终使用项目虚拟环境，避免全局 Python 包版本互相污染。
SYSTEM_PYTHON=$(command -v python3 || true)
if [ -z "$SYSTEM_PYTHON" ]; then
    echo "❌ 未找到 python3，请先安装 Python >= 3.12"
    exit 1
fi

VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "📦 正在创建项目虚拟环境: .venv"
    "$SYSTEM_PYTHON" -m venv "$VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python"
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"

# 检查虚拟环境的 Python 版本
PYTHON_VERSION=$("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.12"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 版本要求 >= $REQUIRED_VERSION，当前版本: $PYTHON_VERSION"
    exit 1
fi
echo "✓ Python 版本: $PYTHON_VERSION ($PYTHON)"

# 检查核心依赖和版本。只检查 fastapi 是否能导入会漏掉版本冲突，
# 例如新版 pydantic-settings 搭配旧版 pydantic。
DEPENDENCIES_OK=true
if ! "$PYTHON" - <<'PY' &>/dev/null
from importlib.metadata import version
from packaging.version import Version

minimum_versions = {
    "pydantic": "2.8.0",
    "pydantic-settings": "2.5.0",
    "fastapi": "0.115.0",
    "uvicorn": "0.30.0",
    "chromadb": "0.5.0",
    "httpx": "0.27.1",
}
for package, minimum in minimum_versions.items():
    assert Version(version(package)) >= Version(minimum), (
        f"{package} {version(package)} < {minimum}"
    )

import chromadb  # noqa: F401
import fastapi  # noqa: F401
import pydantic  # noqa: F401
import pydantic_settings  # noqa: F401
import socksio  # noqa: F401 — required when all_proxy uses socks5://
PY
then
    DEPENDENCIES_OK=false
elif ! "$PYTHON" -m pip check &>/dev/null; then
    DEPENDENCIES_OK=false
fi

if [ "$DEPENDENCIES_OK" != "true" ]; then
    echo ""
    echo "📦 正在安装或修复虚拟环境依赖..."
    "$PYTHON" -m pip install -e ".[dev]"
    "$PYTHON" -m pip check
    echo "✓ 依赖安装完成"
else
    echo "✓ 虚拟环境依赖完整"
fi

# 检查 .env 文件
if [ ! -f "config/.env" ]; then
    echo "⚠️  config/.env 文件不存在，正在创建..."
    if [ -f "config/.env.example" ]; then
        cp config/.env.example config/.env
        echo "⚠️  请编辑 config/.env 填入你的 LLM_API_KEY"
    else
        echo "❌ 找不到 config/.env.example"
        exit 1
    fi
fi

# 检查 API Key
# BSD grep on macOS does not support -P; a portable extended regex is enough
# for the lightweight configuration check performed below.
source <(grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=' config/.env | head -1 2>/dev/null || true)
if grep -q "sk-your-siliconflow-api-key-here" config/.env 2>/dev/null || ! grep -q "LLM_API_KEY=sk-" config/.env; then
    echo "⚠️  请先配置 config/.env 中的 LLM_API_KEY"
    echo "   获取 API Key: https://cloud.siliconflow.cn"
    echo ""
fi

# gRPC-based Milvus/Zilliz connections should bypass HTTP/SOCKS proxies.
# Otherwise grpcio may send the TLS handshake to all_proxy and fail with
# "Handshake read failed". Only the configured host is added; API traffic
# such as SiliconFlow and GitHub can continue to use the user's proxy.
MILVUS_BYPASS_HOST=$("$PYTHON" -c '
from urllib.parse import urlparse
from config.settings import settings

uri = settings.milvus.uri or ""
host = urlparse(uri).hostname if uri else settings.milvus.host
print(host or "")
' 2>/dev/null || true)

if [ -n "$MILVUS_BYPASS_HOST" ]; then
    NO_PROXY_VALUE="${no_proxy:-${NO_PROXY:-}}"
    case ",$NO_PROXY_VALUE," in
        *",$MILVUS_BYPASS_HOST,"*) ;;
        *) NO_PROXY_VALUE="${NO_PROXY_VALUE:+$NO_PROXY_VALUE,}$MILVUS_BYPASS_HOST" ;;
    esac
    export no_proxy="$NO_PROXY_VALUE"
    export NO_PROXY="$NO_PROXY_VALUE"
    echo "✓ Milvus 直连: $MILVUS_BYPASS_HOST"
fi

# 检查示例文档
if [ ! -d "data/sample_docs" ]; then
    echo "⚠️  警告: data/sample_docs 目录不存在，跳过文档索引"
else
    echo ""
    echo "📚 检查示例文档索引状态..."
    # Use the same configured backend as the runtime (Chroma or Milvus).
    if "$PYTHON" -c "
from research_agent.retrieval.vector_store import create_vector_store
vs = create_vector_store()
if vs.count > 0:
    print(f'SKIP:{vs.count}')
" 2>/dev/null | grep -q "SKIP:"; then
        CHUNKS=$("$PYTHON" -c "
from research_agent.retrieval.vector_store import create_vector_store
print(create_vector_store().count)
" 2>/dev/null)
        VECTOR_BACKEND=$("$PYTHON" -c "from config.settings import settings; print(settings.retrieval.vector_backend)" 2>/dev/null)
        echo "   ✓ ${VECTOR_BACKEND} 向量库已有 ${CHUNKS} 个 chunk，跳过索引"
    else
        echo "   (首次运行需要下载 Embedding 模型，请耐心等待)"
        if ! "$PYTHON" -c "
from research_agent.retrieval.vector_store import create_vector_store
from research_agent.retrieval.document_loader import DocumentLoader
from research_agent.retrieval.search_text import INDEX_VERSION
from pathlib import Path

data_dir = Path('data/sample_docs')
loaded_chunks = DocumentLoader().load_directory(data_dir)
chunks = [chunk.content for chunk in loaded_chunks]
chunk_ids = [chunk.chunk_id for chunk in loaded_chunks]
chunk_metas = [
    {
        **chunk.metadata,
        'doc_title': Path(chunk.metadata.get('file_name', '')).stem,
        'source': chunk.metadata.get('file_name', ''),
        'index_version': INDEX_VERSION,
    }
    for chunk in loaded_chunks
]

if chunks:
    print('  ⏳ 加载 Embedding 模型...')
    vs = create_vector_store()
    vs.add_documents(chunk_ids, chunks, chunk_metas)
    print(f'  ✓ {vs.__class__.__name__} 索引完成: {vs.count} 个 chunk')
    print('  ✓ BM25 将在后端启动时从持久向量库自动重建')
else:
    print('  ⚠️  无有效文档块，跳过索引')
" 2>&1; then
            echo "  ⚠️  文档索引失败，服务仍可启动（上传/检索功能可能受影响）"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "  启动服务..."
echo "=========================================="
echo ""
echo "后端 API: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo "前端界面: http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "=========================================="
echo ""

# 创建临时日志目录
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# 启动后端
echo "🚀 启动后端 (FastAPI)..."
"$PYTHON" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动。首次加载向量库和 MCP 可能超过几秒，不能用固定
# sleep 过早判定失败。
BACKEND_READY=false
for _ in $(seq 1 30); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        BACKEND_READY=true
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        break
    fi
    sleep 1
done

if [ "$BACKEND_READY" != "true" ]; then
    echo "❌ 后端启动失败，请检查日志: $LOG_DIR/backend.log"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
echo "✓ 后端启动成功"

# 启动前端 (Vue 3 / Vite)
echo "🚀 启动前端 (Vue 3 + Vite)..."
cd "$SCRIPT_DIR/frontend-vue"

# 首次运行检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "   首次运行，正在安装前端依赖..."
    npm install --silent
    echo "   ✓ 依赖安装完成"
fi

npm run dev -- --host 127.0.0.1 > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"
echo "   前端 PID: $FRONTEND_PID"

# 等待前端启动并打开浏览器
FRONTEND_READY=false
for _ in $(seq 1 30); do
    if curl -s http://localhost:5173/ > /dev/null 2>&1; then
        FRONTEND_READY=true
        break
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        break
    fi
    sleep 1
done

if [ "$FRONTEND_READY" = "true" ]; then
    echo "✓ 前端启动成功"
    echo ""
    echo "✅ 所有服务已启动！"
    echo ""
    echo "🌐 打开浏览器访问: http://localhost:5173"

    # 尝试打开浏览器
    if command -v open &> /dev/null; then
        sleep 1
        open http://localhost:5173 2>/dev/null || true
    fi
else
    echo "❌ 前端启动失败，请检查日志: $LOG_DIR/frontend.log"
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    exit 1
fi

echo ""
echo "=========================================="
echo "  停止服务"
echo "=========================================="
echo ""

# 捕获 Ctrl+C 并停止服务
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "✓ 服务已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 保持脚本运行
echo "按 Ctrl+C 停止服务..."
while true; do
    sleep 1
done
