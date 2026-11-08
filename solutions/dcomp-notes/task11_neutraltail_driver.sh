set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-tailorder solutions/dcomp-t11-taildedup --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c 'Task11 equal final-state repair order and duplicate endpoints' > "$N/t11-neutraltail-gcc.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-neutraltail-gcc "$N/t11-neutraltail-gcc.log" --seeds 0-500 --orders 4 > "$N/t11-neutraltail-gcc-stats.log" 2>&1
DEVAL_CXX=clang++ DEVAL_NATIVE=1 nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-taildedup --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-200 -c 'Task11 duplicate endpoint exact Clang' > "$N/t11-neutraltail-clang.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-neutraltail-clang "$N/t11-neutraltail-clang.log" --seeds 0-200 --orders 4 > "$N/t11-neutraltail-clang-stats.log" 2>&1
