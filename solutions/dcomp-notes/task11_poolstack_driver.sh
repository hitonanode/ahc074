set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-pool10 solutions/dcomp-t11-pool12 --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c "Task11 cheap final repair stacked with efficient secondary parent" > "$N/t11-poolstack.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-poolstack "$N/t11-poolstack.log" --seeds 0-500 --orders 4 > "$N/t11-poolstack-stats.log" 2>&1
