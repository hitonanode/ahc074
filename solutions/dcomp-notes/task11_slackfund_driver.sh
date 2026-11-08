set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-funded-slack30 solutions/dcomp-t11-funded-slack25 --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-500 -c "Task11 final fixed slack funding of extra parent search" > "$N/t11-slackfund.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-slackfund "$N/t11-slackfund.log" --seeds 0-500 --orders 4 > "$N/t11-slackfund-stats.log" 2>&1
DEVAL_CXX=clang++ DEVAL_NATIVE=1 nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-funded-slack30 solutions/dcomp-t11-funded-slack25 --seeds 0-500 -c "Task11 final fixed slack budget native Clang paired 500" > "$N/t11-slackfund-clang.log" 2>&1
flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" t11-slackfund-clang "$N/t11-slackfund-clang.log" --seeds 0-500 > "$N/t11-slackfund-clang-stats.log" 2>&1
