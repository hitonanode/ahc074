#!/usr/bin/env bash
set -euo pipefail
TASK_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
if [[ "${DEVAL_LOCKED:-0}" != 1 ]]; then
    exec flock -x /home/sato/ahc074/runs/.lock env DEVAL_LOCKED=1 bash "$0"
fi
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
mkdir -p "$TASK_DIR/build-tmp"
export TMPDIR="$TASK_DIR/build-tmp"
/home/sato/ahc074/.venv/bin/python "$TASK_DIR/emit_cpp.py"
g++ -std=c++23 -O2 -march=native "$TASK_DIR/bench_value.cpp" -o "$TASK_DIR/bench_value_gcc"
clang++ -std=c++23 -O2 -march=native "$TASK_DIR/bench_value.cpp" -o "$TASK_DIR/bench_value_clang"
/home/sato/ahc074/.venv/bin/python "$TASK_DIR/check_value.py"
