#!/bin/bash
set -euo pipefail

REMOTE_USER="ieeerasufcg"
REMOTE_HOST="mocaprasp-client-3.local"
REMOTE_DIR="/home/$REMOTE_USER/mocap_test"
 # Better to use a dedicated name
BUILD_DIR="$REMOTE_DIR/build"

# Make sure these match exactly what you have on your local machine
FILES=("capture.cpp" "capture.h" "CMakeLists.txt")

echo "[INFO] Cleaning and preparing remote directory..."
# We wipe the build dir to ensure a fresh CMake cache every time
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $BUILD_DIR && rm -rf $BUILD_DIR/*"

echo "[INFO] Transferring files to $REMOTE_HOST..."
scp "${FILES[@]}" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

echo "[INFO] Building and Running..."
ssh "$REMOTE_USER@$REMOTE_HOST" "bash -lc '
    cd \"$BUILD_DIR\" && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j\$(nproc) && \
    echo \"[INFO] Starting Capture...\" && \
    ./capture_app 0 
'"