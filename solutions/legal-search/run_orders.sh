#!/bin/bash
# Runs same_end on single orders listed in ORDER_LIST ("seed r" per line), 23 processes, under the
# evaluation lock with low priority. Output: OUT_DIR/<seed>_<r>.txt
# Usage: run_orders.sh RUN_DIR ORDER_LIST OUT_DIR BUDGET MODE
set -e
RUN_DIR=$1
LIST=$2
OUT=$3
BUDGET=$4
MODE=$5
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
flock -x /home/sato/ahc074/runs/.lock nice -n 10 xargs -P 23 -L 1 sh -c \
  's=$(printf %04d $0); '"$HERE"'/same_end /home/sato/ahc074/tools/in/$s.txt '"$RUN_DIR"'/out/$s.txt $0 '"$BUDGET $MODE"' $1 $(($1 + 1)) > '"$OUT"'/${s}_$1.txt' < "$LIST"
