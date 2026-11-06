"""Training-only summary of the supplied two half-anneal candidates."""
from pathlib import Path
import json
import numpy as np
HERE=Path(__file__).resolve().parent
d=np.load(HERE/'half_selection.npz')
y=d['scores'][:500];pick=d['pick'][:500]
selected=y[np.arange(500),pick]
rows=json.loads(Path('/home/sato/ahc074/runs/20261107-015743_deval-seed/result.json').read_text())['cases']
b=np.array([c['order_scores'] for c in sorted(rows,key=lambda c:int(c['seed'])) if int(c['seed'])<500])
out={'n':500,'designs':['20261107-030039_deval-seed','20261107-030511_deval-seed'],
     'replays':['20261107-030158_deval-seed','20261107-030628_deval-seed']}
for name,sl in [('real',slice(0,1)),('all8',slice(0,8)),('lists1_7',slice(1,8))]:
    z=100*np.log(selected[:,sl].mean(axis=1)/b[:,sl].mean(axis=1))
    out[name]={'mean':float(z.mean()),'se':float(z.std(ddof=1)/len(z)**.5)}
(HERE/'half_reference_500.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
