set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-merge-near solutions/dcomp-t11-merge-collect solutions/dcomp-t11-merge-win --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c 'Task11 compare after exact repeated-move repair' > "$N/t11-mergeearly.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-mergeearly "$N/t11-mergeearly.log" --seeds 0-500 --orders 4 > "$N/t11-mergeearly-stats.log" 2>&1
