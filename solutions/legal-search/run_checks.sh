#!/bin/bash
# Stage 1 follow-up jobs (each under the evaluation lock, released between jobs):
#   plain: the single-move search without assertions / visibility bound (mode 5) on seeds 0-1, to check
#          the pruning against the full search;
#   multi: the restricted multi-move search (mode 2: a paper may move twice, parking slots) on seeds 0-3;
#   unk:   the orders left unknown, again with a larger budget.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
RUN=/home/sato/ahc074/runs/20261107-210226_deval-helper-wide
cd "$HERE"
./run_chunks.sh $RUN "0 1" 12 results/plain 500000 5
./run_chunks.sh $RUN "0 1 2 3" 6 results/multi 300000 2
cat results/stage1/*.txt | awk '$6=="unk"{print $1, $2}' > results/unk_list.txt
./run_orders.sh $RUN results/unk_list.txt results/unk 10000000 0
