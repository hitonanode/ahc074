#!/bin/bash
# Runs same_end on the given seeds, each split into CHUNKS ranges of orders, 23 processes, under the
# evaluation lock with low priority. Output: OUT_DIR/<seed>_<chunk>.txt
# Usage: run_chunks.sh RUN_DIR "SEEDS" CHUNKS OUT_DIR BUDGET MODE
set -e
RUN_DIR=$1
SEEDS=$2
CHUNKS=$3
OUT=$4
BUDGET=$5
MODE=$6
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
for s in $SEEDS; do
  for c in $(seq 0 $((CHUNKS - 1))); do
    a=$((1024 * c / CHUNKS))
    b=$((1024 * (c + 1) / CHUNKS))
    echo "$s $c $a $b"
  done
done | flock -x /home/sato/ahc074/runs/.lock nice -n 10 xargs -P 23 -L 1 sh -c \
  's=$(printf %04d $0); '"$HERE"'/same_end /home/sato/ahc074/tools/in/$s.txt '"$RUN_DIR"'/out/$s.txt $0 '"$BUDGET $MODE"' $2 $3 > '"$OUT"'/${s}_$1.txt'
