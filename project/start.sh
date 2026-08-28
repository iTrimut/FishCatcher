#!/bin/bash
# 一键启动项目服务器
PORT=${1:-8080}
DIR="$(cd "$(dirname "$0")" && pwd)"

# 先杀掉已有的同端口进程
lsof -ti :$PORT | xargs kill 2>/dev/null

cd "$DIR"
echo "项目启动中..."
echo "  入口页: http://localhost:$PORT/"
echo "  界面一: http://localhost:$PORT/aggregator.html"
echo "  界面二: http://localhost:$PORT/organizer.html"
echo "  界面三: http://localhost:$PORT/dashboard.html"
echo ""
echo "按 Ctrl+C 停止服务器"

python3 -m http.server $PORT
