set -eu
N=solutions/dcomp-notes
for cc in gcc clang; do
  if [ "$cc" = clang ]; then export DEVAL_CXX=clang++ DEVAL_NATIVE=1; fi
  nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-holetable --seeds 0-200 -c "Task11 exact hole quotient table $cc" > "$N/t11-holetable-$cc.log" 2>&1
  flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" "t11-holetable-$cc" "$N/t11-holetable-$cc.log" --seeds 0-200 > "$N/t11-holetable-$cc-stats.log" 2>&1
  nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-holecheck --seeds 0-4 --no-record -c "Task11 exact hole quotient exhaustive used-lane checker $cc research" > "$N/t11-holecheck-$cc.log" 2>&1
done
