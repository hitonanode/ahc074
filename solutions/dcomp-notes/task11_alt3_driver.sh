set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-funded-alt3 --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c "Task11 fixed three ALT repairs after expanding ordinary plans" > "$N/t11-alt3.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-alt3 "$N/t11-alt3.log" --seeds 0-500 --orders 4 > "$N/t11-alt3-stats.log" 2>&1
DEVAL_CXX=clang++ DEVAL_NATIVE=1 nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-funded-alt3 --seeds 0-500 -c "Task11 fixed three ALT native Clang time" > "$N/t11-alt3-clang.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-alt3-clang "$N/t11-alt3-clang.log" --seeds 0-500 > "$N/t11-alt3-clang-stats.log" 2>&1
