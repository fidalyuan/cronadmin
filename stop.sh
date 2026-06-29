#!/bin/bash

# CronAdmin 一键停止脚本
# ==========================================

# 1. 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# 2. 确定脚本所在目录并切换
SCRIPT_PATH="$0"
case "$SCRIPT_PATH" in
    /*) DIR=$(dirname "$SCRIPT_PATH") ;;
    *) DIR=$(pwd)/$(dirname "$SCRIPT_PATH") ;;
esac
cd "$DIR" || exit 1

# 3. 环境加载以获取自定义端口
ENV_FILE="./.cronadmin_env"
if [ -f "$ENV_FILE" ]; then
    . "$ENV_FILE"
fi

BACKEND_PORT="${CRONADMIN_PORT:-8342}"
FRONTEND_PORT="5173"

kill_port_process() {
    local port=$1
    local killed=0
    
    if command -v fuser >/dev/null 2>&1; then
        if fuser "$port/tcp" >/dev/null 2>&1; then
            fuser -k "$port/tcp" >/dev/null 2>&1 || true
            killed=1
        fi
    elif command -v lsof >/dev/null 2>&1; then
        local pids
        pids=$(lsof -ti:"$port" 2>/dev/null)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 >/dev/null 2>&1 || true
            killed=1
        fi
    else
        local pid
        pid=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP '(?<=pid=)\d+' | head -n 1)
        if [ -n "$pid" ]; then
            kill -9 "$pid" 2>/dev/null || true
            killed=1
        fi
    fi
    return $killed
}

printf "%b" "${BLUE}>>> 正在停止 CronAdmin 系统...${NC}\n"

# 停止后端
printf "正在清理后端端口占用 (${BACKEND_PORT})...\n"
kill_port_process "${BACKEND_PORT}"
BACKEND_STATUS=$?

# 停止前端
printf "正在清理前端端口占用 (${FRONTEND_PORT})...\n"
kill_port_process "${FRONTEND_PORT}"
FRONTEND_STATUS=$?

sleep 1

printf "\n%b" "${GREEN}==========================================${NC}\n"
printf "%b" "${GREEN}CronAdmin 停止操作完成！${NC}\n"
printf "%b" "${GREEN}==========================================${NC}\n"
