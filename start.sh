#!/bin/bash

# Deep Research Agent 一键启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Deep Research Agent 启动脚本"
echo "=========================================="
echo ""

# 检查 Python 版本
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.12"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 版本要求 >= $REQUIRED_VERSION，当前版本: $PYTHON_VERSION"
    exit 1
fi
echo "✓ Python 版本: $PYTHON_VERSION"

# 检查依赖是否已安装
if ! python3 -c "import fastapi" &>/dev/null; then
    echo ""
    echo "📦 正在安装依赖..."
    pip install -e ".[dev]" -q
    echo "✓ 依赖安装完成"
else
    echo "✓ 依赖已安装"
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
source <(grep -oP '^[^#]*\K\w+=[^=]*' config/.env | head -1 2>/dev/null || true)
if grep -q "sk-your-siliconflow-api-key-here" config/.env 2>/dev/null || ! grep -q "LLM_API_KEY=sk-" config/.env; then
    echo "⚠️  请先配置 config/.env 中的 LLM_API_KEY"
    echo "   获取 API Key: https://cloud.siliconflow.cn"
    echo ""
fi

# 检查示例文档
if [ ! -d "data/sample_docs" ]; then
    echo "⚠️  警告: data/sample_docs 目录不存在，跳过文档索引"
else
    echo ""
    echo "📚 正在索引示例文档..."
    echo "   (首次运行需要下载 Embedding 模型，请耐心等待)"
    python3 -c "
from research_agent.retrieval.vector_store import VectorStore
from research_agent.retrieval.bm25 import BM25Retriever
from pathlib import Path

data_dir = Path('data/sample_docs')
docs = []
for f in data_dir.glob('*.md'):
    with open(f) as fp:
        docs.append((f.stem, fp.read(), {'doc_title': f.stem, 'source': f.name}))

ids = [d[0] for d in docs]
texts = [d[1] for d in docs]
metadatas = [d[2] for d in docs]

chunks = []
chunk_ids = []
chunk_metas = []
for i, text in enumerate(texts):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    for j, para in enumerate(paragraphs):
        if len(para) > 50:
            chunks.append(para)
            chunk_ids.append(f'{ids[i]}_chunk_{j}')
            chunk_metas.append({**metadatas[i], 'chunk_index': j})

print('  ⏳ 加载 Embedding 模型...')
vs = VectorStore()
vs.add_documents(chunk_ids, chunks, chunk_metas)
print(f'  ✓ 向量库索引完成: {vs.count} 个 chunk')

bm25 = BM25Retriever()
bm25.index_documents(chunk_ids, chunks, chunk_metas)
print(f'  ✓ BM25 索引完成: {len(chunks)} 条')
" || echo "  ⚠️  文档索引失败，请检查上方错误信息"
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
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 2

# 检查后端是否启动成功
sleep 2
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
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

npm run dev -- --host 0.0.0.0 > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"
echo "   前端 PID: $FRONTEND_PID"

# 等待前端启动并打开浏览器
sleep 3
if lsof -ti :5173 > /dev/null 2>&1; then
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
