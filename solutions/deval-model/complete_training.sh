#!/usr/bin/env bash
# Complete-data training/validation only. Does NOT evaluate seeds 500..999.
set -euo pipefail
TASK_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
if [[ -z "${DEVAL_MANIFEST:-}" ]]; then
    if [[ -f "$TASK_DIR/runs.tsv" ]] && [[ "$(tail -n 1 "$TASK_DIR/runs.tsv")" == done ]]; then
        export DEVAL_MANIFEST="$TASK_DIR/runs.tsv"
    else
        export DEVAL_MANIFEST=/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/c9c38a4d-6d47-4694-ada6-fce91018e02d/scratchpad/deval/runs.tsv
    fi
fi
if [[ "${DEVAL_LOCKED:-0}" != 1 ]]; then
    while [[ ! -f "$DEVAL_MANIFEST" ]] || [[ "$(tail -n 1 "$DEVAL_MANIFEST")" != done ]]; do sleep 10; done
    exec flock -x /home/sato/ahc074/runs/.lock env DEVAL_LOCKED=1 bash "$0"
fi
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
DEVAL_PY=/home/sato/ahc074/.venv/bin/python
"$DEVAL_PY" "$TASK_DIR/prepare.py" --manifest "$DEVAL_MANIFEST"
for DEVAL_MODE in static filler fast compact markov stationary stationary32 persistent; do
    "$DEVAL_PY" "$TASK_DIR/features.py" --mode "$DEVAL_MODE"
    "$DEVAL_PY" "$TASK_DIR/fit.py" --mode "$DEVAL_MODE" --feature-set all
done
"$DEVAL_PY" "$TASK_DIR/fit.py" --mode static --feature-set baseline --name baseline_calibrated
"$DEVAL_PY" "$TASK_DIR/fit.py" --mode static --feature-set minimal --name analytic_minimal
"$DEVAL_PY" "$TASK_DIR/fit.py" --mode filler --feature-set head --name head_analytic
"$DEVAL_PY" "$TASK_DIR/fit.py" --mode filler --feature-set coupled --name coupled_small
OMP_NUM_THREADS=8 "$DEVAL_PY" "$TASK_DIR/target_model.py" --mode fast --name target_fast
"$DEVAL_PY" "$TASK_DIR/diagnose.py" --mode markov
