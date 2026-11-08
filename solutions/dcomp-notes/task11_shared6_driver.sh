set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-shared6 solutions/dcomp-t11-shared6-alt2 --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c "Task11 reallocate additional ordinary ALT calls to one secondary repair proposal" > "$N/t11-shared6.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-shared6 "$N/t11-shared6.log" --seeds 0-500 --orders 4 > "$N/t11-shared6-stats.log" 2>&1
