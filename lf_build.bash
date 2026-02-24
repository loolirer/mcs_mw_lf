#!/bin/bash

# Exit immediately if any command fails
set -e

PYTHON_SCRIPT="lf_composer.py"
LF_SOURCE="src/MotionTrackingArena.lf"
EXEC_FILE="bin/MotionTrackingArena"
DIST_FILE="bin/MotionTrackingArena_distribute.sh"

echo "[COMPOSER] Composing LF file with Remote RTI (Standard Mode)..."
python3 "$PYTHON_SCRIPT"

echo "[COMPOSER] Compiling LF file (Generating Remote Binaries)..."
lfc "$LF_SOURCE"

echo "[COMPOSER] Distributing for federates..."
if [ -f "$DIST_FILE" ]; then
    ./"$DIST_FILE"
else
    echo "Error: Binary not found at $DIST_FILE"
    exit 1
fi

echo "[COMPOSER] Removing from RTI host machine..."
rm -rf ~/LinguaFrancaRemote

echo "[COMPOSER] Composing LF file with Local RTI (Flag --local-rti)..."
python3 "$PYTHON_SCRIPT" --local-rti

echo "[COMPOSER] Compiling LF file (Generating Local Binary)..."
lfc "$LF_SOURCE"

echo "[COMPOSER] Executing MotionTrackingArena..."
if [ -f "$EXEC_FILE" ]; then
    ./"$EXEC_FILE"
else
    echo "Error: Binary not found at $EXEC_FILE"
    exit 1
fi