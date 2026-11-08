"""Training-only tail decomposition from recorded normal runs. flock + nice."""
from pathlib import Path
import json,re
import numpy as np
R=Path('/home/sato/ahc074/runs');N=Path(__file__).resolve().parent
rx=re.compile(r'^([a-zA-Z][a-zA-Z0-9_]*) = ([-+0-9.eE]+)$',re.M)
out={}
for compiler,rid in [('gcc','20261108-155517_dcomp-combo-alt1'),('clang','20261108-155242_dcomp-combo-alt1')]:
    d=R/rid;assert json.loads((d/'meta.json').read_text())['status']=='ok'
    rows=[{k:float(v) for k,v in rx.findall((d/'err'/f'{s:04d}.txt').read_text())} for s in range(500)]
    keys=set.intersection(*(set(r) for r in rows));x={k:np.array([r[k] for r in rows]) for k in keys}
    x['judge']=x['end_sec']+.04*x['helper_end_sec']+.35*x['req_sec']
    ix=np.argsort(x['judge'])[-25:];req=np.argsort(x['req_sec'])[-25:]
    v={'run':rid,'slow25':list(map(int,ix)),'req25':list(map(int,req)),'stats':{},'request_correlations':[]}
    for k in ['judge','helper_end_sec','req_sec','map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','colmdp_sec','ns_plan_calls','eject_trials','neutral_total','f2_memo_misses','screen_prepared','screen_checked']:
        if k not in x:continue
        z=x[k];v['stats'][k]={'mean':float(z.mean()),'slow25':float(z[ix].mean()),'req25':float(z[req].mean()),'p99':float(np.percentile(z,99))}
    for k,z in x.items():
        if k.endswith('_sec') or np.std(z)==0:continue
        c=float(np.corrcoef(z,x['req_sec'])[0,1]);v['request_correlations'].append([k,c,float(z.mean()),float(z[req].mean())])
    v['request_correlations'].sort(key=lambda z:abs(z[1]),reverse=True)
    out[compiler]=v
    print(compiler,'slow25',v['slow25'])
    for k,q in v['stats'].items():print(k,q)
    print('request correlations',v['request_correlations'][:25])
(N/'t11-tail.json').write_text(json.dumps(out,indent=2)+'\n')
