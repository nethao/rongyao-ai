#!/usr/bin/env bash
# 修改后一键：构建前端 + 重启 backend/frontend
# 用法: ./scripts/refresh-and-restart.sh  或  bash scripts/refresh-and-restart.sh
set -e
cd "$(dirname "$0")/.."
echo ">>> 构建 frontend ..."
docker-compose build frontend
echo ">>> 重启 backend，重建并启动 frontend ..."
docker-compose stop backend frontend 2>/dev/null || true
docker-compose rm -f frontend 2>/dev/null || true
docker-compose up -d backend frontend
echo ">>> 完成。请刷新浏览器查看效果。"
