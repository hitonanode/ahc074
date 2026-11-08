set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" solutions/dcomp-t11-neutral-train --design-from 20261108-155517_combo-m1-nine --seeds 0-200 -c 'Task11 neutral after-repair ranking labels, training0-199 only' > "$N/t11-neutraltrain.log" 2>&1
