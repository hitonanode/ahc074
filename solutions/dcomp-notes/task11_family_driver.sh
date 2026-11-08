set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-family-delete solutions/dcomp-t11-family-merge solutions/dcomp-t11-neutral-seed03 solutions/dcomp-t11-neutral-seed075 --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c 'Task11 repair before moved-paper family collapse and second neutral seed' > "$N/t11-family.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-family "$N/t11-family.log" --seeds 0-500 --orders 4 > "$N/t11-family-stats.log" 2>&1
