set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-stack-one solutions/dcomp-t11-stack-pc6 solutions/dcomp-t11-stack-pl1 --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c 'Task11 stack independent request gains with exact speedups' > "$N/t11-stack-search.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-stack-search "$N/t11-stack-search.log" --seeds 0-500 --orders 4 > "$N/t11-stack-search-stats.log" 2>&1
