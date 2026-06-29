#!/bin/bash

# CronAdmin 一键启动脚本 (鲁棒增强版)
# ==========================================

# 1. 强制设置 UTF-8 语言环境，解决中文乱码问题
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export LANGUAGE=C.UTF-8

# 2. 颜色定义 (兼容 sh/bash/dash)
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# 3. 确定脚本所在目录 (核心：确保在任何目录下执行都能找到依赖)
# 处理 sh 执行时可能获取不到脚本路径的问题
SCRIPT_PATH="$0"
case "$SCRIPT_PATH" in
    /*) DIR=$(dirname "$SCRIPT_PATH") ;;
    *) DIR=$(pwd)/$(dirname "$SCRIPT_PATH") ;;
esac
cd "$DIR" || exit 1

kill_port_process() {
    local port=$1
    # 优先尝试不使用 sudo 杀死进程
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "$port/tcp" >/dev/null 2>&1 || true
    elif command -v lsof >/dev/null 2>&1; then
        lsof -ti:"$port" | xargs -r kill -9 >/dev/null 2>&1 || true
    else
        # 最后的保底手段，尝试通过 ss 查找 pid
        local pid
        pid=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP '(?<=pid=)\d+' | head -n 1)
        [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null || true
    fi
}

printf "%b" "${BLUE}>>> 正在准备启动 CronAdmin 系统...${NC}\n"

# 4. 环境检查与加载
ENV_FILE="./.cronadmin_env"
if [ -f "$ENV_FILE" ]; then
    # 使用 POSIX 标准的点操作符加载，并指定路径
    . "$ENV_FILE"
    PYTASK_PYTHON="$CRONADMIN_PYTHON"
fi

# 智能探测 Python 解释器
if [ -z "$PYTASK_PYTHON" ] || [ ! -x "$PYTASK_PYTHON" ]; then
    if [ -x "./.venv/bin/python3" ]; then
        PYTASK_PYTHON="./.venv/bin/python3"
    elif [ -x "./.venv/bin/python" ]; then
        PYTASK_PYTHON="./.venv/bin/python"
    elif [ -x "$HOME/miniconda3/envs/pytask/bin/python3" ]; then
        PYTASK_PYTHON="$HOME/miniconda3/envs/pytask/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        PYTASK_PYTHON=$(command -v python3)
    fi
fi

# 检查 Python 是否真的存在
if [ -z "$PYTASK_PYTHON" ] || { [ ! -x "$PYTASK_PYTHON" ] && [ ! -f "$PYTASK_PYTHON" ]; }; then
    printf "%b" "${RED}[错误] 未能找到 Python 解释器: ${PYTASK_PYTHON:-(空)}${NC}\n"
    printf "请先运行 ./install.sh 进行初始化配置，或者在当前目录下创建 .venv 虚拟环境。\n"
    exit 1
fi

# 5. 读取运行端口 (默认为 8342)
BACKEND_PORT="${CRONADMIN_PORT:-8342}"

# 6. 清理旧进程
printf "%b" "${BLUE}>>> 正在清理端口占用 (${BACKEND_PORT}, 5173)...${NC}\n"
kill_port_process "${BACKEND_PORT}"
kill_port_process 5173
sleep 1

# 7. 启动后端服务
printf "%b" "${BLUE}>>> 正在启动 FastAPI 后端...${NC}\n"
if [ -d "backend" ]; then
    cd backend
    export PYTHONPATH=.
    # 使用绝对路径启动 Python，确保不受当前 shell 环境(conda)影响
    "$PYTASK_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" > backend_runtime.log 2>&1 &
    BACKEND_PID=$!
    cd ..
else
    printf "%b" "${RED}[错误] 找不到 backend 目录${NC}\n"
    exit 1
fi

# 8. 启动前端服务
printf "%b" "${BLUE}>>> 正在启动 Vue 3 前端...${NC}\n"
if [ -d "frontend" ]; then
    cd frontend
    # 同样使用后台运行
    npm run dev -- --host --port 5173 > frontend_runtime.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
else
    printf "%b" "${RED}[错误] 找不到 frontend 目录${NC}\n"
fi

# 9. 验证启动结果
sleep 2
BACKEND_OK=0
FRONTEND_OK=0

if ps -p "$BACKEND_PID" >/dev/null 2>&1; then BACKEND_OK=1; fi
if ps -p "$FRONTEND_PID" >/dev/null 2>&1; then FRONTEND_OK=1; fi

if [ "$BACKEND_OK" -eq 1 ] && [ "$FRONTEND_OK" -eq 1 ]; then
    printf "\n%b" "${GREEN}==========================================${NC}\n"
    printf "%b" "${GREEN}CronAdmin 系统已全量拉起！${NC}\n"
    printf "%b" "${BLUE}API 接口: ${NC} http://localhost:${BACKEND_PORT}\n"
    printf "%b" "${BLUE}管理界面: ${NC} http://localhost:5173\n"
    printf "%b" "${GREEN}==========================================${NC}\n"
    printf "提示: 输入 'kill $BACKEND_PID $FRONTEND_PID' 可停止服务。\n"
else
    [ "$BACKEND_OK" -eq 0 ] && printf "%b" "${RED}[失败] 后端启动异常，请检查 backend/backend_runtime.log${NC}\n"
    [ "$FRONTEND_OK" -eq 0 ] && printf "%b" "${RED}[失败] 前端启动异常，请检查 frontend/frontend_runtime.log${NC}\n"
fi
