set -eu
N=solutions/dcomp-notes
if [ "$#" -eq 0 ]; then set -- gcc clang; fi
for cc in "$@"; do
 if [ "$cc" = clang ]; then export DEVAL_CXX=clang++ DEVAL_NATIVE=1; fi
 nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-stack-pc6 solutions/dcomp-t11-funded-pc6 solutions/dcomp-t11-funded-shared6 --save-design --seeds 0-500 -c "Task11 normal budget/identity of faster six-plan secondary-parent search $cc" > "$N/t11-funded-$cc.log" 2>&1
 flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" "t11-funded-$cc" "$N/t11-funded-$cc.log" --seeds 0-500 > "$N/t11-funded-$cc-stats.log" 2>&1
 flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task11_funded_identity.py" "$cc" > "$N/t11-funded-$cc-identity.log" 2>&1
done
