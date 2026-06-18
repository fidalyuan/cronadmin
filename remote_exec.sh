#!/bin/bash
~/start_mihomo.sh
sleep 5

export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

podman stop cronadmin-demo 2>/dev/null
podman rm cronadmin-demo 2>/dev/null

podman run -d \
    --network host \
    --name cronadmin-demo \
    -e http_proxy=http://127.0.0.1:7890 \
    -e https_proxy=http://127.0.0.1:7890 \
    -e PIP_BREAK_SYSTEM_PACKAGES=1 \
    debian:stable-slim bash -c "
    export http_proxy=http://127.0.0.1:7890
    export https_proxy=http://127.0.0.1:7890
    export PIP_BREAK_SYSTEM_PACKAGES=1
    apt update && apt install -y --no-install-recommends git curl python3 python3-pip python3-venv nodejs npm procps build-essential && \
    git clone https://github.com/fidalyuan/cronadmin && cd cronadmin && \
    mkdir -p bin && cp tests/mock_whiptail.sh bin/whiptail && \
    chmod +x bin/whiptail && export PATH=\$PWD/bin:\$PATH && \
    ./install.sh && \
    # 修复依赖与代码
    pip install loguru aiofiles pycryptodome 'bcrypt==4.0.1' && \
    sed -i \"s/default_sha256/\\\"admin123\\\"/g\" backend/app/main.py && \
    echo 'export CRONADMIN_PYTHON=\\\"/usr/bin/python3\\\"' > .cronadmin_env && \
    ./start.sh && \
    sleep infinity"
