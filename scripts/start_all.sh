#!/bin/bash
# 一键启动智能坐姿监测系统（Linux/Mac）

set -e

echo "=========================================="
echo "  智能坐姿监测系统 - 一键启动"
echo "=========================================="

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 1. 启动后端
echo "[1/2] 启动 FastAPI 后端..."
cd "$PROJECT_DIR/backend"
pip install -r requirements.txt -q 2>/dev/null
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID → http://localhost:8000"

# 等待后端启动
sleep 2

# 2. 启动前端
echo "[2/2] 启动 Vue3 前端..."
cd "$PROJECT_DIR/frontend"
npm install --silent 2>/dev/null
npm run dev &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID → http://localhost:5173"

echo ""
echo "=========================================="
echo "  启动完成"
echo "  后端: http://localhost:8000"
echo "  前端: http://localhost:5173"
echo "  测试用户: test / 123456"
echo "=========================================="
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
