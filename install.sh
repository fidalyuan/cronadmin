#!/bin/bash

# CronAdmin 智能环境自动化部署脚本 (跨环境鲁棒版)
# ==========================================

# 强制设置 UTF-8 语言环境，解决中文乱码问题
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

# ==========================================
# 0. 环境探测与兼容性工具
# ==========================================
IS_CONTAINER=0
ENV_DESC="物理机/虚拟机 (Host Linux)"
IS_ALPINE=0

if [ -f "/.dockerenv" ] || [ -f "/run/.containerenv" ]; then
    IS_CONTAINER=1
    ENV_DESC="容器环境 (Container / Podman / Docker)"
elif grep -q 'docker\|lxc\|podman' /proc/1/cgroup 2>/dev/null; then
    IS_CONTAINER=1
    ENV_DESC="容器环境 (Container / Control Group)"
fi

if [ -f "/etc/os-release" ] && grep -qi "ID=alpine" /etc/os-release; then
    IS_ALPINE=1
    ENV_DESC+=" [Alpine Linux]"
fi

printf "%b" "${BLUE}>>> 部署向导第一步：环境识别...${NC}\n"
printf "%b" "${GREEN}[检测结果] 当前运行环境: ${ENV_DESC}${NC}\n\n"

SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo &> /dev/null; then
    SUDO="sudo"
fi

PKG_MANAGER=""
if command -v apk &> /dev/null; then PKG_MANAGER="apk";
elif command -v apt-get &> /dev/null; then PKG_MANAGER="apt-get";
elif command -v dnf &> /dev/null; then PKG_MANAGER="dnf";
elif command -v yum &> /dev/null; then PKG_MANAGER="yum";
fi

printf "%b" "${BLUE}>>> 正在识别包管理器: ${PKG_MANAGER:-未知}${NC}\n"

download_file() {
    local url=$1
    local output=$2
    local is_busybox_wget=0
    printf "%b" "${BLUE}>>> 正在请求资源: ${url}${NC}\n"
    
    # 1. 尝试使用 wget
    if command -v wget &> /dev/null; then
        if wget --help 2>&1 | grep -q "BusyBox"; then is_busybox_wget=1; fi
        if wget -c --tries=3 --timeout=30 "$url" -O "$output"; then return 0; fi
        printf "%b" "${BLUE}>>> wget 首次下载失败，正在尝试强制不使用代理重试...${NC}\n"
        if [ "$is_busybox_wget" -eq 1 ]; then 
            if wget -c -Y off --tries=5 "$url" -O "$output"; then return 0; fi
        else 
            if wget -c --no-proxy --tries=5 "$url" -O "$output"; then return 0; fi
        fi
    fi

    # 2. 尝试使用 curl
    if command -v curl &> /dev/null; then
        if curl -L "$url" -o "$output"; then return 0; fi
        printf "%b" "${BLUE}>>> curl 首次下载失败，正在尝试强制不使用代理重试...${NC}\n"
        if curl --noproxy "*" -L "$url" -o "$output"; then return 0; fi
    fi

    # 3. Debian 专属保底：使用 apt-helper
    if [ -x "/usr/lib/apt/apt-helper" ]; then
        printf "%b" "${BLUE}>>> 正在尝试使用 Debian 专用工具 [apt-helper] 下载...${NC}\n"
        if $SUDO /usr/lib/apt/apt-helper download-file "$url" "$output"; then return 0; fi
    fi

    printf "%b" "${RED}[错误] 无法通过 wget, curl 或 apt-helper 下载必要组件。${NC}\n"
    printf "请检查网络连接，或手动安装 wget/curl 后重试。\n"
    return 1
}

if ! command -v whiptail &> /dev/null; then
    printf "%b" "${BLUE}>>> 核心组件 [whiptail] 缺失，正在尝试为您自动安装...${NC}\n"
    case $PKG_MANAGER in
        apk) $SUDO apk add --update newt ;;
        apt-get) 
            if ! $SUDO apt-get update; then
                printf "%b" "${RED}[警告] apt-get update 失败，正在尝试禁用代理重试...${NC}\n"
                unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
                $SUDO apt-get update
            fi
            $SUDO apt-get install -y whiptail
            ;;
        dnf|yum) $SUDO $PKG_MANAGER install -y newt ;;
    esac

    if ! command -v whiptail &> /dev/null; then
        printf "%b" "${RED}[错误] 无法自动安装 whiptail。${NC}\n"
        printf "这通常是因为没有 Root 权限、软件源未配置或网络不通。\n"
        printf "请尝试手动执行安装命令后再运行此脚本。\n"
        exit 1
    else
        printf "%b" "${GREEN}[成功] whiptail 已自动安装并就绪。${NC}\n"
    fi
fi

# ==========================================
# 1. 探测包管理器与原生 Python
# ==========================================
CONDA_EXE=""
for p in "conda" "mamba" "$HOME/miniconda3/bin/conda" "$HOME/anaconda3/bin/conda" "$HOME/miniforge3/bin/conda" "$HOME/miniforge3/bin/mamba"; do
    if command -v "$p" &> /dev/null; then CONDA_EXE=$(command -v "$p"); break;
    elif [ -x "$p" ]; then CONDA_EXE="$p"; break; fi
done
NATIVE_PY=$(command -v python3 || echo "")
SETUP_ACTION=""
NEW_ENV_NAME=""
NEW_PY_VER="3.10"
FINAL_PY=""

# ==========================================
# 2. 交互式环境确认逻辑
# ==========================================
if [ -n "$CONDA_EXE" ]; then
    MANAGER_NAME=$(basename "$CONDA_EXE")
    ENV_LINES=$("$CONDA_EXE" env list | grep -v '^#' | awk 'NF>0' | sed 's/*//g')
    
    MENU_OPTIONS=()
    # 要求：原生 Python 放在第一位
    if [ -n "$NATIVE_PY" ]; then
        MENU_OPTIONS+=("$NATIVE_PY" "使用系统原生 Python")
    fi
    
    # 填充已有的 Conda 环境
    while read -r line; do
        name=$(echo "$line" | awk '{print $1}'); path=$(echo "$line" | awk '{print $NF}')
        [ "$name" = "$path" ] && name="(基础环境)"; MENU_OPTIONS+=("$path" "Conda 环境: $name")
    done <<< "$ENV_LINES"
    
    MENU_OPTIONS+=("CREATE_NEW" "++ 创建新的虚拟环境 ++")
    
    CHOICE=$(whiptail --title "选择 Python 环境" --menu "请选择部署策略（优先展示原生环境）：" 20 75 10 "${MENU_OPTIONS[@]}" 3>&1 1>&2 2>&3)
    [ -z "$CHOICE" ] && exit 0

    if [ "$CHOICE" = "CREATE_NEW" ]; then
        NEW_ENV_NAME=$(whiptail --title "新建虚拟环境" --inputbox "请输入新虚拟环境的名称:" 10 60 "pytask" 3>&1 1>&2 2>&3)
        [ -z "$NEW_ENV_NAME" ] && exit 0
        NEW_PY_VER=$(whiptail --title "Python 版本选择" --inputbox "请输入要安装的 Python 版本:" 10 60 "3.10" 3>&1 1>&2 2>&3)
        [ -z "$NEW_PY_VER" ] && exit 0
        SETUP_ACTION="CREATE_CONDA"
    elif [ "$CHOICE" = "$NATIVE_PY" ]; then
        SETUP_ACTION="USE_EXISTING"; FINAL_PY="$NATIVE_PY"
    else
        SETUP_ACTION="USE_EXISTING"; FINAL_PY="$CHOICE/bin/python"
    fi
else
    # 没有任何虚拟环境管理器 (Conda/Miniforge) 的情况
    if [ -n "$NATIVE_PY" ]; then
        if [ "$IS_ALPINE" -eq 1 ]; then
            if whiptail --title "环境确认" --yesno "检测到 Alpine 已安装原生 Python: $NATIVE_PY\n\n建议直接使用此环境以确保系统稳定性。\n\n是否确认使用？" 12 70; then
                SETUP_ACTION="USE_EXISTING"; FINAL_PY="$NATIVE_PY"
            else
                NEW_ENV_NAME=$(whiptail --title "安装虚拟环境" --inputbox "警告：Alpine 下 Conda 极其臃肿且易报错。\n\n若坚持安装，请输入环境名称:" 12 70 "pytask" 3>&1 1>&2 2>&3)
                [ -z "$NEW_ENV_NAME" ] && exit 0
                NEW_PY_VER=$(whiptail --title "Python 版本选择" --inputbox "请输入 Python 版本:" 10 60 "3.10" 3>&1 1>&2 2>&3)
                [ -z "$NEW_PY_VER" ] && exit 0
                SETUP_ACTION="INSTALL_MINICONDA"
            fi
        else
            # 非 Alpine 且有原生 Python：原生放在第一位
            CHOICE=$(whiptail --title "Python 环境选择" --menu "系统发现了原生 Python，但未检测到 Conda。\n请选择您的部署策略：" 15 75 2 \
                "1" "使用系统原生 Python ($NATIVE_PY)" \
                "2" "下载并安装新版 Miniconda (实现环境隔离) [推荐]" 3>&1 1>&2 2>&3)
            
            case $CHOICE in
                "1") SETUP_ACTION="USE_EXISTING"; FINAL_PY="$NATIVE_PY" ;;
                "2") 
                    NEW_ENV_NAME=$(whiptail --title "新建虚拟环境" --inputbox "请输入新虚拟环境的名称:" 10 60 "pytask" 3>&1 1>&2 2>&3)
                    [ -z "$NEW_ENV_NAME" ] && exit 0
                    NEW_PY_VER=$(whiptail --title "Python 版本选择" --inputbox "请输入要安装的 Python 版本:" 10 60 "3.10" 3>&1 1>&2 2>&3)
                    [ -z "$NEW_PY_VER" ] && exit 0
                    SETUP_ACTION="INSTALL_MINICONDA"
                    ;;
                *) exit 0 ;;
            esac
        fi
    else
        if [ "$IS_ALPINE" -eq 1 ]; then
            if whiptail --title "Alpine 部署建议" --yesno "检测到您正在使用纯净的 Alpine Linux 且未安装 Python。\n\n在该环境下不推荐使用 Miniconda/Miniforge。\n\n建议直接安装系统原生 Python 3 环境 (最稳定)。\n\n您是否同意此建议？" 15 70; then
                SETUP_ACTION="INSTALL_NATIVE_PY"; FINAL_PY="/usr/bin/python3"
            else
                NEW_ENV_NAME=$(whiptail --title "安装虚拟环境" --inputbox "请输入新虚拟环境名称 (通过 Miniforge 创建):" 10 60 "pytask" 3>&1 1>&2 2>&3)
                [ -z "$NEW_ENV_NAME" ] && exit 0
                NEW_PY_VER=$(whiptail --title "Python 版本选择" --inputbox "请输入 Python 版本:" 10 60 "3.10" 3>&1 1>&2 2>&3)
                [ -z "$NEW_PY_VER" ] && exit 0
                SETUP_ACTION="INSTALL_MINICONDA"
            fi
        else
            whiptail --title "环境缺失" --msgbox "系统未检测到任何 Python 环境。\n\n我们将引导您下载并安装 Miniconda 以创建虚拟环境。" 10 70
            NEW_ENV_NAME=$(whiptail --title "新建虚拟环境" --inputbox "请输入新虚拟环境名称:" 10 60 "pytask" 3>&1 1>&2 2>&3)
            [ -z "$NEW_ENV_NAME" ] && exit 0
            NEW_PY_VER=$(whiptail --title "Python 版本选择" --inputbox "请输入要安装的 Python 版本:" 10 60 "3.10" 3>&1 1>&2 2>&3)
            [ -z "$NEW_PY_VER" ] && exit 0
            SETUP_ACTION="INSTALL_MINICONDA"
        fi
    fi
fi

# 3. 探测 Node.js
NEEDS_NODE=0; NODE_MSG=""
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    NODE_MSG="[*] 自动安装 Node.js 和 npm\n"; NEEDS_NODE=1
else NODE_MSG="[跳过] Node.js ($(node -v)) 已就绪\n"; fi

# ==========================================
# 4. 汇总确认
# ==========================================
SUMMARY="配置清单:\n\n"
if [ "$SETUP_ACTION" = "USE_EXISTING" ]; then SUMMARY+="[*] 使用现有 Python: $FINAL_PY\n";
elif [ "$SETUP_ACTION" = "INSTALL_NATIVE_PY" ]; then SUMMARY+="[*] [推荐] 安装系统原生 Python 3 和 Pip\n";
elif [ "$SETUP_ACTION" = "CREATE_CONDA" ]; then SUMMARY+="[*] 在 $MANAGER_NAME 中创建环境: '$NEW_ENV_NAME' (Python $NEW_PY_VER)\n";
elif [ "$SETUP_ACTION" = "INSTALL_MINICONDA" ]; then 
    if [ "$IS_ALPINE" -eq 1 ]; then SUMMARY+="[*] 部署 Miniforge3 (musl版)\n"; else SUMMARY+="[*] 部署官方 Miniconda3\n"; fi
    SUMMARY+="[*] 创建环境: '$NEW_ENV_NAME' (Python $NEW_PY_VER)\n"; fi
SUMMARY+="$NODE_MSG[*] 安装系统依赖与后端/前端依赖库\n"

if ! whiptail --title "CronAdmin 安装确认" --yesno "$SUMMARY\n确认无误开始安装吗？" 20 75; then exit 0; fi

# ==========================================
# 5. 执行逻辑
# ==========================================
printf "\n%b" "${GREEN}>>> 开始部署...${NC}\n"

# 5.1 安装 Node.js
if [ "$NEEDS_NODE" -eq 1 ]; then
    printf "%b" "${BLUE}>>> 正在从系统软件源安装 Node.js...${NC}\n"
    case $PKG_MANAGER in
        apk) $SUDO apk add --update nodejs npm ;;
        apt-get) 
            if ! $SUDO apt-get update; then
                printf "%b" "${RED}[警告] apt-get update 失败，正在尝试禁用代理重试...${NC}\n"
                unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
                $SUDO apt-get update
            fi
            $SUDO apt-get install -y nodejs npm ;;
        dnf) $SUDO dnf install -y nodejs npm ;;
        yum) $SUDO yum install -y nodejs npm ;;
    esac
fi

# 5.2 安装 Python 环境
if [ "$SETUP_ACTION" = "INSTALL_NATIVE_PY" ]; then
    printf "%b" "${BLUE}>>> 正在安装原生 Python 3 和相关组件...${NC}\n"
    $SUDO apk add --update python3 py3-pip python3-dev build-base
elif [ "$SETUP_ACTION" = "INSTALL_MINICONDA" ]; then
    MC_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    MF_URL="https://github.com/conda-forge/miniforge/releases/download/24.3.0-0/Miniforge3-Linux-musl-x86_64.sh"
    INST_NAME="conda_installer.sh"
    if [ "$IS_ALPINE" -eq 1 ]; then
        download_file "$MF_URL" "$INST_NAME" || exit 1
        bash "$INST_NAME" -b -p "$HOME/miniconda3"
    else
        download_file "$MC_URL" "$INST_NAME" || exit 1
        if ! bash "$INST_NAME" -b -p "$HOME/miniconda3"; then
            printf "%b" "${RED}标准版失败，切换至 Miniforge...${NC}\n"
            rm -rf "$HOME/miniconda3"; download_file "$MF_URL" "$INST_NAME" || exit 1
            bash "$INST_NAME" -b -p "$HOME/miniconda3"
        fi
    fi
    rm -f "$INST_NAME"
    CONDA_PATH="$HOME/miniconda3/bin/conda"
    [ ! -f "$CONDA_PATH" ] && CONDA_PATH="$HOME/miniconda3/bin/mamba"
    eval "$($CONDA_PATH shell.bash hook)"
    if "$CONDA_PATH" tos accept --help &>/dev/null; then
        "$CONDA_PATH" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main 2>/dev/null || true
    fi
    printf "%b" "${BLUE}>>> 正在创建虚拟环境 '$NEW_ENV_NAME' (Python $NEW_PY_VER)...${NC}\n"
    if ! "$CONDA_PATH" create -y -n "$NEW_ENV_NAME" python="$NEW_PY_VER"; then
        "$CONDA_PATH" create -y -n "$NEW_ENV_NAME" python="$NEW_PY_VER" -c conda-forge --override-channels
    fi
    FINAL_PY="$HOME/miniconda3/envs/$NEW_ENV_NAME/bin/python"
    [ ! -f "$FINAL_PY" ] && FINAL_PY="$HOME/miniconda3/envs/$NEW_ENV_NAME/bin/python3"
elif [ "$SETUP_ACTION" = "CREATE_CONDA" ]; then
    eval "$($CONDA_EXE shell.bash hook)"
    printf "%b" "${BLUE}>>> 正在创建环境 '$NEW_ENV_NAME' (Python $NEW_PY_VER)...${NC}\n"
    if ! "$CONDA_EXE" create -y -n "$NEW_ENV_NAME" python="$NEW_PY_VER"; then
        "$CONDA_EXE" create -y -n "$NEW_ENV_NAME" python="$NEW_PY_VER" -c conda-forge --override-channels
    fi
    FINAL_PY=$("$CONDA_EXE" env list | grep "$NEW_ENV_NAME" | awk '{print $NF}')/bin/python
    [ ! -f "$FINAL_PY" ] && FINAL_PY=$(dirname "$FINAL_PY")/python3
fi

# 5.3 依赖安装
PIP_FLAGS=""
[ "$IS_ALPINE" -eq 1 ] && PIP_FLAGS="--break-system-packages"
if [ -d "backend" ]; then
    printf "%b" "${BLUE}>>> 正在安装后端依赖库...${NC}\n"
    cd backend && "$FINAL_PY" -m pip install -r requirements.txt $PIP_FLAGS && cd ..
fi
if [ -d "frontend" ]; then
    printf "%b" "${BLUE}>>> 正在安装前端依赖库...${NC}\n"
    cd frontend && npm install && cd ..
fi

# 5.4 保存配置
echo "export CRONADMIN_PYTHON=\"$FINAL_PY\"" > .cronadmin_env
if [ -d "backend" ]; then
    echo "export CRONADMIN_PYTHON=\"$FINAL_PY\"" > backend/.cronadmin_env
fi

printf "\n%b" "${GREEN}✨ 部署圆满完成！${NC}\n"
printf "已选 Python: %b\n" "${BLUE}$FINAL_PY${NC}"
printf "启动命令: ${GREEN}./start.sh${NC}\n"
