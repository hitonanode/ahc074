set -eu
N=solutions/dcomp-notes
for cc in gcc clang gccnative; do
 unset DEVAL_CXX DEVAL_NATIVE || true
 seeds=0-500
 if [ "$cc" = clang ]; then export DEVAL_CXX=clang++ DEVAL_NATIVE=1; fi
 if [ "$cc" = gccnative ]; then export DEVAL_NATIVE=1; seeds=0-200; fi
 nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-fast-late --save-design --seeds "$seeds" -c "Task11 exact combined late memo and direct geometry identity/time $cc" > "$N/t11-fastlate-$cc.log" 2>&1
 flock -x /home/sato/ahc074/runs/.lock nice -n 10 /home/sato/ahc074/.venv/bin/python "$N/task10_analyze_log.py" "t11-fastlate-$cc" "$N/t11-fastlate-$cc.log" --seeds "$seeds" > "$N/t11-fastlate-$cc-stats.log" 2>&1
done
