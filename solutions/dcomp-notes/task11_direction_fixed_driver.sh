set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-dircompact solutions/dcomp-t11-dirpdep solutions/dcomp-t11-dirmask --seeds 0-200 -c 'Task11 direction SIMD expansion GCC explicit lambda AVX2 targets' > "$N/t11-direction-fixed-gcc.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-direction-fixed-gcc "$N/t11-direction-fixed-gcc.log" --seeds 0-200 > "$N/t11-direction-fixed-gcc-stats.log" 2>&1
