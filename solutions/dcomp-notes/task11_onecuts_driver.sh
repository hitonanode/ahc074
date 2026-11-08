set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-one-early solutions/dcomp-t11-one-late solutions/dcomp-t11-one-deep solutions/dcomp-t11-one-shallow --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c 'Task11 fixed one-to-one endpoint/time budgets on alt1' > "$N/t11-onecuts.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-onecuts "$N/t11-onecuts.log" --seeds 0-500 --orders 4 > "$N/t11-onecuts-stats.log" 2>&1
