set -eu
N=solutions/dcomp-notes
nice -n 10 python3 "$N/task10_run.py" --compare solutions/dcomp-combo-alt1 solutions/dcomp-t11-tie-train --design-from 20261108-155517_combo-m1-nine --seeds 0-4 -c 'Task11 new-policy tie rollout labels pilot, training seeds only' > "$N/t11-tietrain-pilot.log" 2>&1
python3 - <<'PY' > solutions/dcomp-notes/t11-tietrain-runs.txt
from pathlib import Path
import json,re
ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',Path('solutions/dcomp-notes/t11-tietrain-pilot.log').read_text(),re.M)
assert len(ids)==2
R=Path('/home/sato/ahc074/runs')
for r in ids:
 assert json.loads((R/r/'meta.json').read_text())['status']=='ok'
 cs=json.loads((R/r/'result.json').read_text())['cases'];assert len(cs)==4 and all(c['score']>0 for c in cs)
 assert max(c['execution_time'] for c in cs)<50
for seed in range(4):assert (R/ids[0]/'out'/f'{seed:04d}.txt').read_bytes()==(R/ids[1]/'out'/f'{seed:04d}.txt').read_bytes()
print(' '.join(ids))
PY
read -r base probe < "$N/t11-tietrain-runs.txt"
nice -n 10 python3 scripts/pahcer_run.py --extend "$base" "$probe" --seeds 4-300 -c 'Task11 rollout labels fixed alt1 policy, seeds0-199 fit /200-299 validate' > "$N/t11-tietrain-extend.log" 2>&1
