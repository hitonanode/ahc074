#!/bin/bash
# Usage: solutions/dsel-probe/run_salts.sh SEEDS ORDERS SALT... (run from the repo root)
# For each salt: save the designs of dsel-probe with DESIGN_SALT=salt on SEEDS, then evaluate the
# saved designs on ORDERS order sequences (--design-from --orders). Prints "salt run_design run_orders".
# Extra environment (e.g. DESIGN_SALT_STAGES) is passed through to the solution.
set -e
seeds=$1; orders=$2; shift 2
for s in "$@"; do
  log=$(DESIGN_SALT=$s python3 scripts/pahcer_run.py ${SOL:-solutions/dsel-probe} --seeds $seeds --save-design --no-record \
        -c "dsel-probe salt $s stages ${DESIGN_SALT_STAGES:-31} ${TAG}: 設計の保存" 2>&1)
  run=$(echo "$log" | grep -o '20[0-9]\{6\}-[0-9]\{6\}_[a-z0-9-]*' | head -1)
  log2=$(python3 scripts/pahcer_run.py ${SOL:-solutions/dsel-probe} --design-from $run --orders $orders --seeds $seeds \
        -c "dsel-probe salt $s stages ${DESIGN_SALT_STAGES:-31} ${TAG}: orders $orders" 2>&1)
  run2=$(echo "$log2" | grep -o '20[0-9]\{6\}-[0-9]\{6\}_[a-z0-9-]*' | head -1)
  echo "$s $run $run2"
done
