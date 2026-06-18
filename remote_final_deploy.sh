#!/bin/bash
echo ">>> 正在清理旧容器..."
podman stop cronadmin-demo 2>/dev/null
podman rm cronadmin-demo 2>/dev/null

echo ">>> 正在启动代理..."
~/start_mihomo.sh
sleep 5

echo ">>> 正在启动新容器 (Debian Slim)..."
podman run -d \
    --network host \
    --name cronadmin-demo \
    -e http_proxy=http://127.0.0.1:7890 \
    -e https_proxy=http://127.0.0.1:7890 \
    -e PIP_BREAK_SYSTEM_PACKAGES=1 \
    debian:stable-slim bash -c '
    export http_proxy=http://127.0.0.1:7890
    export https_proxy=http://127.0.0.1:7890
    export PIP_BREAK_SYSTEM_PACKAGES=1
    
    echo ">>> 安装系统依赖..."
    apt update && apt install -y --no-install-recommends git curl python3 python3-pip python3-venv nodejs npm procps build-essential && \
    
    echo ">>> 克隆项目..."
    git clone https://github.com/fidalyuan/cronadmin && cd cronadmin && \
    
    echo ">>> 安装并修复 Python 依赖..."
    pip install loguru aiofiles pycryptodome "bcrypt==4.0.1" && \
    
    echo ">>> 自动化配置..."
    mkdir -p bin && cp tests/mock_whiptail.sh bin/whiptail && \
    chmod +x bin/whiptail && export PATH=$PWD/bin:$PATH && \
    ./install.sh && \
    
    echo ">>> 修复代码 Bug (Passlib 密码长度限制)..."
    sed -i "s/default_sha256/\"admin123\"/g" backend/app/main.py && \
    echo "export CRONADMIN_PYTHON=\"/usr/bin/python3\"" > .cronadmin_env && \
    
    echo ">>> 正式启动..."
    ./start.sh && \
    printf "\n\033[0;32m>>> 完美的 Demo 系统已全量拉起！\033[0m\n" && \
    sleep infinity'
