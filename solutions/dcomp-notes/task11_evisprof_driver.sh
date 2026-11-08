set -eu
N=solutions/dcomp-notes
for cc in gcc clang; do
 if [ "$cc" = clang ]; then export DEVAL_CXX=clang++ DEVAL_NATIVE=1; fi
 nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-evis-prof --design-from 20261108-155517_combo-m1-nine --seeds 0-200 -c "Task11 profile eject visibility work $cc" > "$N/t11-evisprof-$cc.log" 2>&1
 flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" "t11-evisprof-$cc" "$N/t11-evisprof-$cc.log" --seeds 0-200 > "$N/t11-evisprof-$cc-stats.log" 2>&1
done
