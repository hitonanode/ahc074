"""Average only completed training profiling data, under the common lock."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
R=Path('/home/sato/ahc074/runs/20261107-175520_deval-prof6')
assert json.loads((R/'meta.json').read_text())['status']=='ok'
rows=json.loads((R/'metrics.json').read_text())['cases'];assert len(rows)==100
assert max(map(int,rows))<500
names=[k for k in next(iter(rows.values()))['stderr'] if k.startswith(('cfprof_','af_','dp_'))]
out={'run':R.name,'n':len(rows),'means':{k:sum(r['stderr'][k] for r in rows.values())/len(rows) for k in names if all(k in r['stderr'] for r in rows.values())},'use':'hotspot diagnosis only; timing claims use normal 24-parallel compares'}
(P/'profile.json').write_text(json.dumps(out,indent=2)+'\n')
for k,v in sorted(out['means'].items()):
    if k.endswith(('_exc','_sec')):print(k,v)
