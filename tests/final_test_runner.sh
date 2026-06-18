#!/bin/bash
# Definitive Test Runner for CronAdmin

IMAGES=("debian:stable-slim" "debian:latest" "ubuntu:22.04" "ubuntu:latest" "alpine:latest")

echo "CronAdmin Cross-Platform Deployment Report"
echo "=========================================="

for img in "${IMAGES[@]}"; do
    echo -n "[...] Testing $img... "
    
    rm -f .cronadmin_env
    
    # Run containerized test
    podman run --rm --net=host -v "$(pwd):/app" -w /app "$img" /bin/sh -c "
        # 1. Distro-specific pre-setup
        if command -v apk &>/dev/null; then
            apk add --update bash wget curl ca-certificates newt shadow >/dev/null 2>&1
        else
            apt-get update -qq && apt-get install -y -qq wget curl ca-certificates libnewt0.52 sudo >/dev/null 2>&1
        fi
        
        # 2. Mock interactive UI
        cp tests/mock_whiptail.sh /usr/bin/whiptail && chmod +x /usr/bin/whiptail
        
        # 3. Execute Installation
        export DEBIAN_FRONTEND=noninteractive
        /bin/bash ./install.sh > /tmp/install_test.log 2>&1
        
        # 4. Verify
        if [ -f .cronadmin_env ]; then
            source .cronadmin_env
            if \"\$CRONADMIN_PYTHON\" --version >/dev/null 2>&1 && node -v >/dev/null 2>&1; then
                exit 0
            fi
        fi
        exit 1
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "\e[32m[SUCCESS]\e[0m"
    else
        echo -e "\e[31m[FAILED]\e[0m"
    fi
done
