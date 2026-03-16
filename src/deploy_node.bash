#!/bin/bash
set -euo pipefail

REMOTE_USER="linguafranca"
REMOTE_HOST="raspmcs03.local"
REMOTE_DIR="/home/$REMOTE_USER/tmp"
BUILD_DIR="$REMOTE_DIR/build"

FILES=("capture.cpp" "capture.h" "CMakeLists.txt")

echo "[INFO] Preparing remote directory..."
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $BUILD_DIR"

echo "[INFO] Transferring files to $REMOTE_HOST..."
for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        scp "$file" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"
    else
        echo "[WARNING] $file not found locally, skipping."
    fi
done

echo "[INFO] Running CMake and Building..."
ssh "$REMOTE_USER@$REMOTE_HOST" "bash -lc '
    cd \"$REMOTE_DIR/build\" && \
    cmake .. && \
    make -j\$(nproc) && \
    echo \"[INFO] Starting Capture\" && \
    libcamerify ./capture_app 0 
'"