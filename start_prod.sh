#!/bin/bash

# CronAdmin 生产环境启动脚本 (API 与前端打包托管单端口版)
# ==========================================

# 1. 强制设置 UTF-8 语言环境，解决中文乱码问题
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export LANGUAGE=C.UTF-8

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# 2. 确定脚本所在目录
SCRIPT_PATH="$0"
case "$SCRIPT_PATH" in
    /*) DIR=$(dirname "$SCRIPT_PATH") ;;
    *) DIR=$(pwd)/$(dirname "$SCRIPT_PATH") ;;
esac
cd "$DIR" || exit 1

kill_port_process() {
    local port=$1
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "$port/tcp" >/dev/null 2>&1 || true
    elif command -v lsof >/dev/null 2>&1; then
        lsof -ti:"$port" | xargs -r kill -9 >/dev/null 2>&1 || true
    else
        local pid
        pid=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP '(?<=pid=)\d+' | head -n 1)
        [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null || true
    fi
}

# 3. 环境加载
ENV_FILE="./.cronadmin_env"
if [ -f "$ENV_FILE" ]; then
    . "$ENV_FILE"
    PYTASK_PYTHON="$CRONADMIN_PYTHON"
else
    PYTASK_PYTHON="$HOME/miniconda3/envs/pytask/bin/python3"
fi

if [ ! -x "$PYTASK_PYTHON" ] && [ ! -f "$PYTASK_PYTHON" ]; then
    printf "%b" "${RED}[错误] 未能找到 Python 解释器: $PYTASK_PYTHON${NC}\n"
    printf "请先运行 ./install.sh 进行初始化配置。\n"
    exit 1
fi

# 4. 检查打包结果
if [ ! -d "frontend/dist" ]; then
    printf "%b" "${RED}[错误] 未找到 frontend/dist 目录，请先运行 ./build.sh 进行前端编译打包。${NC}\n"
    exit 1
fi

# 5. 读取运行模式与端口 (默认模式: prod，端口默认为 8342)
MODE="prod"
if [ "$1" = "demo" ]; then
    MODE="demo"
    printf "%b" "${GREEN}>>> 正在以 Demo 模式启动...${NC}\n"
else
    printf "%b" "${GREEN}>>> 正在以 Prod 模式启动...${NC}\n"
fi
export CRONADMIN_MODE="$MODE"

PROD_PORT="${CRONADMIN_PORT:-8342}"

# 6. 清理端口占用 (生产环境只使用配置端口)
printf "%b" "${BLUE}>>> 正在清理端口占用 (${PROD_PORT})...${NC}\n"
kill_port_process "${PROD_PORT}"
sleep 1

# 7. 启动后端服务 (同时托管前端静态文件)
printf "%b" "${BLUE}>>> 正在启动生产环境服务 (API + 前端静态托管，端口: ${PROD_PORT})...${NC}\n"
if [ -d "backend" ]; then
    cd backend
    export PYTHONPATH=.
    "$PYTASK_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "${PROD_PORT}" > backend_runtime.log 2>&1 &
    BACKEND_PID=$!
    cd ..
else
    printf "%b" "${RED}[错误] 找不到 backend 目录${NC}\n"
    exit 1
fi

# 8. 验证启动
sleep 2
if ps -p "$BACKEND_PID" >/dev/null 2>&1; then
    printf "\n%b" "${GREEN}==========================================${NC}\n"
    printf "%b" "${GREEN}CronAdmin 生产版服务已成功拉起！${NC}\n"
    printf "%b" "${BLUE}系统访问地址: ${NC} http://localhost:${PROD_PORT}\n"
    printf "%b" "${BLUE}运行模式:     ${NC} ${MODE}\n"
    printf "%b" "${BLUE}说明: 后端已直接挂载并托管前端 dist 静态目录，单端口流畅运行。${NC}\n"
    printf "%b" "${GREEN}==========================================${NC}\n"
    printf "提示: 输入 'kill $BACKEND_PID' 可停止服务。\n"
else
    printf "%b" "${RED}[失败] 后端启动异常，请检查 backend/backend_runtime.log${NC}\n"
fi
