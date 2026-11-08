set -eu
N=solutions/dcomp-notes
for cc in gcc clang; do
  if [ "$cc" = clang ]; then export DEVAL_CXX=clang++ DEVAL_NATIVE=1; fi
  nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-hash4 solutions/dcomp-t11-hash8 --design-from 20261108-155517_combo-m1-nine --orders 4 --seeds 0-200 -c "Task11 end memo hash exact $cc" > "$N/t11-hash-$cc.log" 2>&1
  flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" "t11-hash-$cc" "$N/t11-hash-$cc.log" --seeds 0-200 --orders 4 > "$N/t11-hash-$cc-stats.log" 2>&1
  nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-design-prof --seeds 0-500 --no-record -c "Task11 normal design profile research $cc" > "$N/t11-design-prof-$cc.log" 2>&1
  flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" "t11-design-prof-$cc" "$N/t11-design-prof-$cc.log" --seeds 0-500 > "$N/t11-design-prof-$cc-stats.log" 2>&1
done
