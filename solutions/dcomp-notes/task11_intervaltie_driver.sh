set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-interval-add solutions/dcomp-t11-interval-replace --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c 'Task11 joint interval equal optimum alternatives' > "$N/t11-interval.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-interval "$N/t11-interval.log" --seeds 0-500 --orders 4 > "$N/t11-interval-stats.log" 2>&1
