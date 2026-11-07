#!/bin/bash
# Runs same_end on seeds [A, B) of a run, 23 processes, under the evaluation lock with low priority.
# Usage: run_stage1.sh RUN_DIR A B OUT_DIR [budget] [mode]
set -e
RUN_DIR=$1
A=$2
B=$3
OUT=$4
BUDGET=${5:-3000000}
MODE=${6:-0}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
seq "$A" $((B - 1)) | flock -x /home/sato/ahc074/runs/.lock nice -n 10 xargs -P 23 -I{} sh -c \
  "s=\$(printf %04d {}); $HERE/same_end /home/sato/ahc074/tools/in/\$s.txt $RUN_DIR/out/\$s.txt {} $BUDGET $MODE > $OUT/\$s.txt"
