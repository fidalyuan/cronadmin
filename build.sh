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
    if npm run build; then
        printf "%b" "${GREEN}✨ [成功] 前端打包完成，已生成 frontend/dist 目录！${NC}\n"
        printf "现在您可以使用 ${GREEN}./start_prod.sh${NC} 来启动生产环境服务了。\n"
    else
        printf "%b" "${RED}❌ [错误] 前端编译打包失败，请检查报错日志。${NC}\n"
        exit 1
    fi
    cd ..
else
    printf "%b" "${RED}[错误] 找不到 frontend 目录${NC}\n"
    exit 1
fi
