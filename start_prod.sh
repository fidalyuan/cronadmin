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
fi

# 智能探测 Python 解释器
if [ -z "$PYTASK_PYTHON" ] || [ ! -x "$PYTASK_PYTHON" ]; then
    if [ -x "./.venv/bin/python3" ]; then
        PYTASK_PYTHON="./.venv/bin/python3"
    elif [ -x "./.venv/bin/python" ]; then
        PYTASK_PYTHON="./.venv/bin/python"
    elif [ -x "../pytask/bin/python3" ]; then
        PYTASK_PYTHON="../pytask/bin/python3"
    elif [ -x "../pytask/bin/python" ]; then
        PYTASK_PYTHON="../pytask/bin/python"
    elif [ -x "$HOME/pytask/bin/python3" ]; then
        PYTASK_PYTHON="$HOME/pytask/bin/python3"
    elif [ -x "$HOME/pytask/bin/python" ]; then
        PYTASK_PYTHON="$HOME/pytask/bin/python"
    elif [ -x "$HOME/miniconda3/envs/pytask/bin/python3" ]; then
        PYTASK_PYTHON="$HOME/miniconda3/envs/pytask/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        PYTASK_PYTHON=$(command -v python3)
    fi
fi

# 将相对路径转换为绝对路径，避免 cd 到子目录后找不到解释器
if [ -n "$PYTASK_PYTHON" ] && [ -x "$PYTASK_PYTHON" ]; then
    PYTASK_PYTHON=$(readlink -f "$PYTASK_PYTHON")
fi

# 检查 Python 是否真的存在
if [ -z "$PYTASK_PYTHON" ] || { [ ! -x "$PYTASK_PYTHON" ] && [ ! -f "$PYTASK_PYTHON" ]; }; then
    printf "%b" "${RED}[错误] 未能找到 Python 解释器: ${PYTASK_PYTHON:-(空)}${NC}\n"
    printf "请先运行 ./install.sh 进行初始化配置，或者在当前目录下创建 .venv 虚拟环境。\n"
    exit 1
fi

# 4. 读取运行模式与端口 (默认模式: prod，端口默认为 8342)
MODE="prod"
if [ "$1" = "demo" ]; then
    MODE="demo"
    printf "%b" "${GREEN}>>> 正在以 Demo 模式启动...${NC}\n"
elif [ "$1" = "dev" ]; then
    MODE="dev"
    printf "%b" "${GREEN}>>> 正在以 Dev (开发) 模式启动...${NC}\n"
else
    printf "%b" "${GREEN}>>> 正在以 Prod 模式启动...${NC}\n"
fi
export CRONADMIN_MODE="$MODE"

PROD_PORT="${CRONADMIN_PORT:-8342}"

# 5. 检查打包结果 (在 dev 模式下跳过该检查)
if [ "$MODE" != "dev" ]; then
    if [ ! -d "frontend/dist" ]; then
        printf "%b" "${RED}[错误] 未找到 frontend/dist 目录，请先运行 ./build.sh 进行前端编译打包。${NC}\n"
        exit 1
    fi
fi

# 6. 清理端口占用 (只使用配置端口)
printf "%b" "${BLUE}>>> 正在清理端口占用 (${PROD_PORT})...${NC}\n"
kill_port_process "${PROD_PORT}"
if [ "$MODE" = "dev" ]; then
    printf "%b" "${BLUE}>>> 正在清理前端开发端口 (5173)...${NC}\n"
    kill_port_process "5173"
fi
sleep 1

# 7. 启动后端服务
if [ "$MODE" = "dev" ]; then
    printf "%b" "${BLUE}>>> 正在启动开发环境服务 (API 单服务带热重载，端口: ${PROD_PORT})...${NC}\n"
else
    printf "%b" "${BLUE}>>> 正在启动生产环境服务 (API + 前端静态托管，端口: ${PROD_PORT})...${NC}\n"
fi

if [ -d "backend" ]; then
    cd backend || exit 1
    export PYTHONPATH=.
    if [ "$MODE" = "dev" ]; then
        # 开发模式：启用 --reload，方便代码热更新
        "$PYTASK_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "${PROD_PORT}" --reload > backend_runtime.log 2>&1 &
    else
        "$PYTASK_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "${PROD_PORT}" > backend_runtime.log 2>&1 &
    fi
    BACKEND_PID=$!
    cd ..
else
    printf "%b" "${RED}[错误] 找不到 backend 目录${NC}\n"
    exit 1
fi

# 8. 如果是 dev 模式，在后台启动前端 Vite 开发服务器
FRONTEND_PID=""
if [ "$MODE" = "dev" ]; then
    if [ -d "frontend" ]; then
        printf "%b" "${BLUE}>>> 正在后台启动前端开发服务 (Vite, 端口: 5173)...${NC}\n"
        cd frontend || exit 1
        npm run dev > frontend_runtime.log 2>&1 &
        FRONTEND_PID=$!
        cd ..
    else
        printf "%b" "${RED}[警告] 找不到 frontend 目录，未能自动启动前端服务。${NC}\n"
    fi
fi

# 9. 验证启动
sleep 2
if ps -p "$BACKEND_PID" >/dev/null 2>&1; then
    printf "\n%b" "${GREEN}==========================================${NC}\n"
    if [ "$MODE" = "dev" ]; then
        printf "%b" "${GREEN}CronAdmin 开发版服务已成功拉起！${NC}\n"
        printf "%b" "${BLUE}前端开发地址 (浏览器访问): ${NC} http://localhost:5173\n"
        printf "%b" "${BLUE}后端 API 地址:           ${NC} http://localhost:${PROD_PORT}\n"
        printf "%b" "${BLUE}运行模式:                 ${NC} ${MODE}\n"
        printf "%b" "${BLUE}说明: 后端已开启热重载，前端已由 Vite 在后台拉起并完成 API 代理配置。${NC}\n"
        printf "%b" "${GREEN}==========================================${NC}\n"
        if [ -n "$FRONTEND_PID" ]; then
            printf "提示: 输入 'kill $BACKEND_PID $FRONTEND_PID' 可停止所有开发服务。\n"
        else
            printf "提示: 输入 'kill $BACKEND_PID' 可停止服务。\n"
        fi
    else
        printf "%b" "${GREEN}CronAdmin 生产版服务已成功拉起！${NC}\n"
        printf "%b" "${BLUE}系统访问地址: ${NC} http://localhost:${PROD_PORT}\n"
        printf "%b" "${BLUE}运行模式:     ${NC} ${MODE}\n"
        printf "%b" "${BLUE}说明: 后端已直接挂载并托管前端 dist 静态目录，单端口流畅运行。${NC}\n"
        printf "%b" "${GREEN}==========================================${NC}\n"
        printf "提示: 输入 'kill $BACKEND_PID' 可停止服务。\n"
    fi
else
    printf "%b" "${RED}[失败] 后端启动异常，请检查 backend/backend_runtime.log${NC}\n"
fi
