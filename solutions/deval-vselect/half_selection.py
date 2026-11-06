"""Evaluate V selection on the independently supplied half-anneal designs."""
from pathlib import Path
import sys, subprocess, json, re
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'deval-model'))
from prepare import state_file,read_state
RUNS=Path('/home/sato/ahc074/runs')
designs=['20261107-030039_deval-seed','20261107-030511_deval-seed']
replays=['20261107-030158_deval-seed','20261107-030628_deval-seed']
base='20261107-015743_deval-seed'
paths=[str(state_file(d,s)) for s in range(1000) for d in designs]
result=subprocess.run([str(HERE/'value_batch')],input='\n'.join(paths)+'\n',text=True,capture_output=True,check=True)
v=np.array([float(x) for x in result.stdout.split()]).reshape(1000,2)
def scores(r):
    cs=json.loads((RUNS/r/'result.json').read_text())['cases']
    return np.array([c['order_scores'] for c in sorted(cs,key=lambda c:int(c['seed']))])
y=np.stack([scores(r) for r in replays],axis=1)
yb=scores(base)
pick=v.argmin(axis=1)
yp=y[np.arange(1000),pick]
output={'chosen':np.bincount(pick,minlength=2).tolist()}
for name,sl in [('real',slice(0,1)),('all8',slice(0,8)),('lists1_7',slice(1,8))]:
    z=100*np.log(yp[:,sl].mean(axis=1)/yb[:,sl].mean(axis=1))
    output[name]={'mean':z.mean(),'se':z.std(ddof=1)/len(z)**.5}
# The integrated split2 solver should produce these same states (except metadata).
errors=[]
keys=['M','G','H','permutation','A','edge','polarity','papers','columns','ded','handle']
for s in range(20):
    chosen=read_state(state_file('20261107-030931_deval-vselect',s))
    expected=read_state(state_file(designs[pick[s]],s))
    if any(chosen[k]!=expected[k] for k in keys): errors.append(s)
output['integrated_state_mismatches']=errors
(HERE/'half_selection.json').write_text(json.dumps(output,indent=2))
np.savez_compressed(HERE/'half_selection.npz',value=v,scores=y,pick=pick)
print(json.dumps(output,indent=2))
