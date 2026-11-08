set -eu
N=solutions/dcomp-notes
for cc in gcc clang; do
 if [ "$cc" = clang ]; then export DEVAL_CXX=clang++ DEVAL_NATIVE=1; fi
 nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-stack-one solutions/dcomp-t11-stack-width12 solutions/dcomp-t11-tight12 --save-design --seeds 0-500 -c "Task11 actual normal time of frozen training stacks $cc" > "$N/t11-stacktime-$cc.log" 2>&1
 flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" "t11-stacktime-$cc" "$N/t11-stacktime-$cc.log" --seeds 0-500 > "$N/t11-stacktime-$cc-stats.log" 2>&1
done
