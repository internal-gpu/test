#!/bin/bash
# 合同审查工具启动脚本

echo "=== 合同审查工具 ==="

# Start backend
echo "启动后端服务 (端口 8000)..."
cd "$(dirname "$0")/backend"
python3 main.py &
BACKEND_PID=$!

# Start frontend dev server
echo "启动前端服务 (端口 5173)..."
cd "$(dirname "$0")/frontend"
npx vite --host &
FRONTEND_PID=$!

echo ""
echo "✓ 后端运行在: http://localhost:8000"
echo "✓ 前端运行在: http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
