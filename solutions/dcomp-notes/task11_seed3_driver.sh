set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-seedone-g015 solutions/dcomp-t11-seedone-g075 solutions/dcomp-t11-seedone-early solutions/dcomp-t11-seedone-expanded --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c 'Task11 refine positive secondary 1-to-1 neutral seed' > "$N/t11-seed3.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-seed3 "$N/t11-seed3.log" --seeds 0-500 --orders 4 > "$N/t11-seed3-stats.log" 2>&1
