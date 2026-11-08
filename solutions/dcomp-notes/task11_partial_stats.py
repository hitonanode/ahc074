from pathlib import Path
import json,re,numpy as np
R=Path('/home/sato/ahc074/runs');N=Path(__file__).resolve().parent
rx=re.compile(r'^([a-zA-Z][a-zA-Z0-9_]*) = ([-+0-9.eE]+)$',re.M)
out={}
for cc in ['gcc','clang']:
 log=N/f't11-partial-{cc}.log'
 if not log.exists():continue
 ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',log.read_text(),re.M)
 if len(ids)<2:continue
 if any(json.loads((R/rid/'meta.json').read_text()).get('status')!='ok' for rid in ids):continue
 a=[];b=[]
 for rid,rows in zip(ids[:2],[a,b]):
  for seed in range(500):
   vals=[]
   for j in range(4):
    p=R/rid/(f'orders/{j}/err' if j else 'err')/f'{seed:04d}.txt'
    vals.append({k:float(v) for k,v in rx.findall(p.read_text())})
   keys=set.intersection(*(set(v) for v in vals))
   rows.append({k:np.mean([v[k] for v in vals]) for k in keys})
 keys=set(a[0])
 print(cc,'keys',sorted(k for k in keys if 'colmdp' in k or k in ['H','columns','model_col']))
 # H is known from the saved design's number of handles in its @paper/column roles.
 covered=np.array([x['colmdp_columns'] for x in a]); req=np.array([x['req_sec'] for x in a]);delta=np.array([y['req_sec']-x['req_sec'] for x,y in zip(a,b)])
 active=np.array([y['partial_mdp_hits']+y['partial_mdp_misses']>0 for y in b]);ix=np.argsort(req)[-25:]
 groups={'all':np.arange(500),'partial':np.flatnonzero(active),'full':np.flatnonzero(~active),'req_slow25':ix}
 v={}
 for key,ii in groups.items():
  z=delta[ii]*1000
  v[key]={'n':len(ii),'delta_ms':float(z.mean()) if len(ii) else None,'se_ms':float(z.std(ddof=1)/np.sqrt(len(ii))) if len(ii)>1 else None,'base_ms':float(req[ii].mean()*1000) if len(ii) else None}
 v['hits']=sum(y['partial_mdp_hits'] for y in b);v['misses']=sum(y['partial_mdp_misses'] for y in b)
 out[cc]=v;print(cc,json.dumps(v))
(N/'t11-partial-groups.json').write_text(json.dumps(out,indent=2)+'\n')
