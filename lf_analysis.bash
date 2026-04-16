#!/bin/bash

# --- Configuration ---
# Default values if not provided by the user
START=${1:-1000}    # Start value in us
END=${2:-10000}     # End value in us
STEP=${3:-500}      # Step in us (e.g., 500 us = 0.5 ms)

CONFIG_FILE="lf_config.yaml"
OUTPUT_DIR="outputs"

mkdir -p "$OUTPUT_DIR"

echo "--------------------------------------------------------"
echo "Starting t_on sweep from ${START}us to ${END}us"
echo "Step size: ${STEP}us"
echo "Output directory: ${OUTPUT_DIR}/"
echo "--------------------------------------------------------"

# Loop through the range
for (( val=$START; val<=$END; val+=$STEP ))
do
    echo "[$(date +%T)] Testing t_on_us = $val ..."

    sed -i "s/t_on_us: [0-9]*/t_on_us: $val/" "$CONFIG_FILE"

    bash lf_build.bash | tee "${OUTPUT_DIR}/output_${val}.txt"

    echo "[$(date +%T)] Finished t_on_us = $val. Log saved."
    echo "--------------------------------------------------------"
done

echo "Sweep complete! Check the '${OUTPUT_DIR}' folder for results."