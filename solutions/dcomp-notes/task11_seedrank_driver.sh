set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-t11-seed-one solutions/dcomp-t11-seedrank-tie solutions/dcomp-t11-seedrank-length --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c "Task11 select second repair parent at same budget" > "$N/t11-seedrank.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-seedrank "$N/t11-seedrank.log" --seeds 0-500 --orders 4 > "$N/t11-seedrank-stats.log" 2>&1
