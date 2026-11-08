set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-ns2 solutions/dcomp-t11-pl1 solutions/dcomp-t11-exp4 solutions/dcomp-t11-width12 solutions/dcomp-t11-slack0 solutions/dcomp-t11-pc6 solutions/dcomp-t11-menu-wide --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c 'Task11 residual menu, cuts and larger-budget research ceiling' > "$N/t11-menu2.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-menu2 "$N/t11-menu2.log" --seeds 0-500 --orders 4 > "$N/t11-menu2-stats.log" 2>&1
