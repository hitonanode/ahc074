#!/usr/bin/env bash
set -euo pipefail
TASK_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
if [[ "${DEVAL_LOCKED:-0}" != 1 ]]; then
    exec flock -x /home/sato/ahc074/runs/.lock env DEVAL_LOCKED=1 bash "$0" "$@"
fi
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
DEVAL_PY=/home/sato/ahc074/.venv/bin/python
"$DEVAL_PY" "$TASK_DIR/prepare.py"
"$DEVAL_PY" "$TASK_DIR/features.py" --mode "${1:-static}"
"$DEVAL_PY" "$TASK_DIR/fit.py" --mode "${1:-static}" --feature-set baseline --name baseline_calibrated
"$DEVAL_PY" "$TASK_DIR/fit.py" --mode "${1:-static}" --feature-set minimal --name analytic_minimal
"$DEVAL_PY" "$TASK_DIR/fit.py" --mode "${1:-static}" --feature-set all
if [[ "${1:-static}" == filler ]]; then
    "$DEVAL_PY" "$TASK_DIR/fit.py" --mode "${1:-static}" --feature-set head --name head_analytic
    "$DEVAL_PY" "$TASK_DIR/fit.py" --mode "${1:-static}" --feature-set coupled --name coupled_small
    "$DEVAL_PY" "$TASK_DIR/diagnose.py" --mode "${1:-static}"
fi
