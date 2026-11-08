set -eu
N=solutions/dcomp-notes
DEVAL_CXX=clang++ DEVAL_NATIVE=1 nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-validmask --seeds 0-500 -c 'Task11 Clang compatible mask reuse exact normal500' > "$N/t11-validmask-clang.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-validmask-clang "$N/t11-validmask-clang.log" --seeds 0-500 > "$N/t11-validmask-clang-stats.log" 2>&1
