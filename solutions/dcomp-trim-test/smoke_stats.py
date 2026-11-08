"""Analyze the completed recorded-by-pahcer, no-record smoke. Use flock/nice."""
from pathlib import Path
import json,re,hashlib
import numpy as np
D=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',(D/'smoke.log').read_text(),re.M);assert len(ids)==2
rx=re.compile(r'^([A-Za-z][A-Za-z_0-9]*) = ([-+0-9.eE]+)$',re.M)
def stat(x):
 x=np.array(x,float);return {'mean':float(x.mean()),'se':float(x.std(ddof=1)/np.sqrt(len(x))),'p99':float(np.percentile(x,99)),'max':float(x.max())}
out={'runs':ids,'times':{},'paired':{},'validation':{}};rows=[]
for rid,source in zip(ids,['time-original.cpp','time-production.cpp']):
 d=R/rid;m=json.loads((d/'meta.json').read_text());cs=json.loads((d/'result.json').read_text())['cases']
 assert m['status']=='ok'and not m['record']and len(cs)==200 and all(c['score']>0 for c in cs)
 assert sorted(int(c['seed'])for c in cs)==list(range(200))
 cmd=m['compile_command'];assert '-ULOCAL_BENCH'in cmd and'-DCLOCK_SCALE=1.1'in cmd
 assert'-DLOCAL_BENCH'not in cmd and'g++'in cmd and'-ftrivial-auto-var-init=zero'in cmd
 assert hashlib.sha256((d/'src'/source).read_bytes()).digest()==hashlib.sha256((D/source).read_bytes()).digest()
 metrics=json.loads((d/'metrics.json').read_text())['cases'];E=sum(v['E']for v in metrics.values());assert E==0
 rr=[{k:float(v)for k,v in rx.findall((d/'err'/f'{i:04d}.txt').read_text())}for i in range(200)]
 assert all(q['dv_candidates']==9 and q['design_time_budget_sec']==1.22 for q in rr)
 rows.append(rr);out['times'][rid]={k:stat([v[k]for v in rr])for k in ['helper_end_sec','req_sec','end_sec']}
 out['validation'][rid]={'status':m['status'],'record':m['record'],'cases':len(cs),'WA':0,'E':E,'compile_command':cmd,'outside_load':m.get('outside_load')}
for k in ['helper_end_sec','req_sec','end_sec']:out['paired'][k]=stat([b[k]-a[k]for a,b in zip(*rows)])
(D/'smoke-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
