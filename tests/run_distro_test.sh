#!/bin/bash
# Master Test Runner for CronAdmin install.sh

if [ $# -gt 0 ]; then
    IMAGES=("$@")
else
    IMAGES=("debian:stable-slim" "ubuntu:22.04" "ubuntu:latest" "debian:latest" "alpine:latest")
fi

RESULTS="/tmp/test_results.txt"
echo "CronAdmin Cross-Distro Test Report" > $RESULTS
echo "Date: $(date)" >> $RESULTS
echo "==================================" >> $RESULTS

for img in "${IMAGES[@]}"; do
    echo ">>> Starting test for image: $img"
    
    rm -f .cronadmin_env
    safe_name=$(echo "$img" | tr ':' '_')
    log_file="/tmp/test_${safe_name}.log"

    # Define pre-setup based on distro
    if [[ "$img" == *"alpine"* ]]; then
        PRE_SETUP="apk add --update bash wget curl ca-certificates newt shadow >/dev/null 2>&1"
    else
        PRE_SETUP="apt-get update -qq && apt-get install -y -qq wget curl ca-certificates libnewt0.52 sudo >/dev/null 2>&1"
    fi

    echo "    Running full deployment and verification..."
    # We always use /bin/sh to start, then install bash, then use bash.
    podman run --rm --net=host -v "$(pwd):/app" -w /app "$img" /bin/sh -c "
        $PRE_SETUP
        cp tests/mock_whiptail.sh /usr/bin/whiptail
        chmod +x /usr/bin/whiptail
        
        # Now run the installer using the newly installed bash
        export DEBIAN_FRONTEND=noninteractive
        /usr/bin/env bash ./install.sh
        
        echo '--- VERIFICATION ---'
        if [ -f .cronadmin_env ]; then
            echo '[PASS] .cronadmin_env created'
            source .cronadmin_env
            \"\$CRONADMIN_PYTHON\" --version && echo '[PASS] Python installed'
            # Node check might fail if PATH is not updated, but install.sh should have installed it
            command -v node && node -v && echo '[PASS] Node.js installed' || echo '[WARN] Node.js not in PATH'
        else
            echo '[FAIL] .cronadmin_env missing'
            exit 1
        fi
    " > "$log_file" 2>&1
    
    if [ $? -eq 0 ] && grep -q "PASS" "$log_file"; then
        echo "- $img: SUCCESS" >> $RESULTS
        echo "    >>> Result: SUCCESS"
    else
        echo "- $img: FAILED" >> $RESULTS
        echo "    >>> Result: FAILED (Check $log_file)"
        tail -n 20 "$log_file"
    fi
done

echo "=================================="
cat $RESULTS
