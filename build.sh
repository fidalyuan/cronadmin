#!/bin/bash

# CronAdmin 前端打包脚本
# ==========================================

# 1. 强制设置 UTF-8 语言环境
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export LANGUAGE=C.UTF-8

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# 自动寻找用户自定义安装路径下的 node/npm 并加入 PATH
for custom_bin in "$HOME/install"/node-*/bin "$HOME/.nvm"/versions/node/*/bin "/usr/local/node"/bin; do
    if [ -d "$custom_bin" ] && [ -x "$custom_bin/node" ] && [ -x "$custom_bin/npm" ]; then
        export PATH="$custom_bin:$PATH"
        break
    fi
done

# 2. 确定脚本所在目录
SCRIPT_PATH="$0"
case "$SCRIPT_PATH" in
    /*) DIR=$(dirname "$SCRIPT_PATH") ;;
    *) DIR=$(pwd)/$(dirname "$SCRIPT_PATH") ;;
esac
cd "$DIR" || exit 1

# 3. 执行打包
printf "%b" "${BLUE}>>> 正在构建前端生产包 (npm run build)...${NC}\n"
if [ -d "frontend" ]; then
    cd frontend
    # 打包前先清理旧的 dist 目录
    rm -rf dist
    if npm run build; then
        printf "%b" "${GREEN}✨ [成功] 前端打包完成，已生成 frontend/dist 目录！${NC}\n"
        cd ..

        # 提示是否上传服务器
        printf "\n是否上传到服务器？[y/N]: "
        read -r UPLOAD_CONFIRM
        if [ "$UPLOAD_CONFIRM" = "y" ] || [ "$UPLOAD_CONFIRM" = "Y" ]; then
            TIMESTAMP=$(date +%Y%m%d%H%M%S)
            TAR_NAME="dist_${TIMESTAMP}.tar.gz"
            printf "%b" "${BLUE}>>> 正在打包生成 ${TAR_NAME}...${NC}\n"
            tar -czf "$TAR_NAME" -C frontend dist

            # 寻找 sshlogin 别名来获得远程主机信息
            SSH_CMD=""
            for f in "$HOME/.bashrc" "$HOME/.bash_aliases" "$HOME/.zshrc"; do
                if [ -f "$f" ]; then
                    SSH_CMD=$(grep "alias sshlogin=" "$f" | sed -E "s/alias sshlogin='(.*)'/\1/")
                    [ -n "$SSH_CMD" ] && break
                fi
            done

            if [ -z "$SSH_CMD" ]; then
                REMOTE_HOST="star@tigy.com.cn"
            else
                REMOTE_HOST=$(echo "$SSH_CMD" | awk '{print $NF}')
            fi

            printf "%b" "${BLUE}>>> 正在上传到云主机 ${REMOTE_HOST}:/home/star/app/...${NC}\n"
            if scp "$TAR_NAME" "${REMOTE_HOST}:/home/star/app/"; then
                printf "%b" "${GREEN}✨ [成功] 上传完成！${NC}\n"
            else
                printf "%b" "${RED}❌ [错误] 上传失败，请检查 SSH/SCP 连接。${NC}\n"
            fi
        fi
        printf "现在您可以使用 ${GREEN}./start_prod.sh${NC} 来启动生产环境服务了。\n"
    else
        printf "%b" "${RED}❌ [错误] 前端编译打包失败，请检查报错日志。${NC}\n"
        cd ..
        exit 1
    fi
else
    printf "%b" "${RED}[错误] 找不到 frontend 目录${NC}\n"
    exit 1
fi
