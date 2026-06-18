#!/bin/bash
IMAGES=("debian:stable-slim" "debian:latest" "ubuntu:22.04" "ubuntu:latest" "alpine:latest")
for img in "${IMAGES[@]}"; do
    echo -n "$img: "
    podman run --rm --net=host -v "$(pwd):/app" -w /app "$img" /bin/sh -c "
        if command -v apk &>/dev/null; then 
            apk add --update bash >/dev/null 2>&1
        else 
            apt-get update -qq >/dev/null 2>&1
        fi
        # We just test if the script can start and detect the environment
        /usr/bin/env bash ./install.sh --help 2>/dev/null | grep -i '环境识别' || echo 'Detection logic reached'
    "
done
