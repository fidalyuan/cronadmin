#!/bin/bash

# 1. 尝试寻找 sshlogin 别名
# 检查常见配置文件
SEARCH_FILES=("$HOME/.bashrc" "$HOME/.bash_aliases" "$HOME/.zshrc")
SSH_CMD=""

for f in "${SEARCH_FILES[@]}"; do
    if [ -f "$f" ]; then
        SSH_CMD=$(grep "alias sshlogin=" "$f" | sed -E "s/alias sshlogin='(.*)'/\1/")
        [ -n "$SSH_CMD" ] && break
    fi
done

if [ -z "$SSH_CMD" ]; then
    echo "错误: 无法在 .bashrc 或 .bash_aliases 中找到 sshlogin 别名。"
    echo "请手动执行以下命令，或者告诉我您的 SSH 登录命令（如 ssh user@host）。"
    exit 1
fi

echo "检测到登录命令: $SSH_CMD"
echo "正在远程主机启动代理并部署 Demo..."

# 2. 执行远程部署
# 先执行代理脚本，然后在 podman run 中传入代理环境变量
$SSH_CMD "source ~/start_mihomo.sh && source ~/proxy.sh && \
    podman run -d --rm \
    -p 8000:8000 -p 5173:5173 \
    --name cronadmin-demo \
    -e http_proxy=http://127.0.0.1:7890 \
    -e https_proxy=http://127.0.0.1:7890 \
    -e all_proxy=socks5://127.0.0.1:7890 \
    debian:stable-slim bash -c '
    export http_proxy=http://127.0.0.1:7890
    export https_proxy=http://127.0.0.1:7890
    apt update && apt install -y --no-install-recommends git curl python3 python3-pip nodejs npm procps && \
    git clone https://github.com/fidalyuan/cronadmin && cd cronadmin && \
    mkdir -p bin && cp tests/mock_whiptail.sh bin/whiptail && \
    chmod +x bin/whiptail && export PATH=\$PWD/bin:\$PATH && \
    ./install.sh && ./start.sh && \
    printf \"\n\033[0;32m>>> 完美的 Demo 系统已拉起（已挂载代理）！\033[0m\n\" && \
    sleep infinity
'"

if [ $? -eq 0 ]; then
    echo "------------------------------------------------"
    echo "部署指令已成功发送至远程主机！"
    echo "系统正在后台进行初始化（安装依赖、拉取代码等，约需 1-2 分钟）。"
    echo "完成后，您可以通过 http://远程主机IP:5173 访问管理界面。"
    echo "提示: 您可以使用 '$SSH_CMD \"podman logs -f cronadmin-demo\"' 查看进度。"
    echo "------------------------------------------------"
else
    echo "部署失败，请检查 SSH 连接或远程主机上的 Podman 状态。"
fi
