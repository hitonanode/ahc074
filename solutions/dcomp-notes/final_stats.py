"""Final paired comparisons and paired bootstrap for the judge-model p99."""
from pathlib import Path
import json,math,re
import numpy as np
N=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
m=json.loads((N/'final-runs.json').read_text());ids=m['final-normal'];rx=re.compile(r'^([a-zA-Z][a-zA-Z0-9_]*) = ([-+0-9.eE]+)$',re.M)
def summary(x):
 x=np.asarray(x,float);return {'n':len(x),'mean':float(x.mean()),'se':float(x.std(ddof=1)/math.sqrt(len(x))),'p99':float(np.percentile(x,99)),'max':float(x.max())}
def read(rid):
 d=R/rid;meta=json.loads((d/'meta.json').read_text());assert meta['status']=='ok'
 cs=sorted(json.loads((d/'result.json').read_text())['cases'],key=lambda c:int(c['seed']))
 assert [int(c['seed']) for c in cs]==list(range(2000)) and all(c['score']>0 for c in cs)
 a=[]
 for i in range(2000):
  z={k:float(v) for k,v in rx.findall((d/'err'/f'{i:04d}.txt').read_text())}
  z['judge_sec']=1.04*z['helper_end_sec']+1.35*z['req_sec']+z['end_sec']-z['helper_end_sec']-z['req_sec'];a.append(z)
 return np.array([c['score'] for c in cs]),{k:np.array([z[k] for z in a]) for k in ['helper_end_sec','req_sec','end_sec','judge_sec','dv_candidates'] if all(k in z for z in a)},meta
loaded={rid:read(rid) for rid in ids};base=ids[2];chosen=ids[3];assert np.all(loaded[chosen][1]['dv_candidates']==9);out={'runs':ids,'compare':{},'timing':{},'outside_load':{r:loaded[r][2].get('outside_load') for r in ids}}
for ref in ids[:-1]:
 x=loaded[ref][0];y=loaded[chosen][0];q={}
 for label,lo,hi in [('all',0,2000),('0-999',0,1000),('1000-1999',1000,2000),('train',0,500),('500-999',500,1000),('500-1999',500,2000)]:
  d=y[lo:hi]-x[lo:hi];q[label]={'pct':summary(100*np.log(y[lo:hi]/x[lo:hi])),'moves':summary(d/1024),'wtl':[int(sum(d<0)),int(sum(d==0)),int(sum(d>0))]}
 out['compare'][ref]=q
for rid in ids:
 a=loaded[rid][1];out['timing'][rid]={k:summary(v) for k,v in a.items()}
 out['timing'][rid]['judge_ratio_argon']=float(a['judge_sec'].mean()/loaded[ids[0]][1]['judge_sec'].mean())
 out['timing'][rid]['end_above']={str(t):int(sum(a['end_sec']>t)) for t in [1.8,1.9,2.]}
b=loaded[base][1];c=loaded[chosen][1]
out['paired']={k:summary(c[k]-b[k]) for k in ['helper_end_sec','req_sec','end_sec','judge_sec']}
rng=np.random.default_rng(20261108);vals=[]
for j in range(40):
 ii=rng.integers(0,2000,(100,2000));vals.extend(np.percentile(c['judge_sec'][ii],99,axis=1)-np.percentile(b['judge_sec'][ii],99,axis=1))
out['p99_paired_bootstrap']={'difference':float(np.percentile(c['judge_sec'],99)-np.percentile(b['judge_sec'],99)),'se':float(np.std(vals,ddof=1)),'ci95':list(map(float,np.percentile(vals,[2.5,97.5]))),'resamples':4000,'rng_seed':20261108}
# The replay must reproduce the chosen design and real-list request policy.
rep=json.loads((R/m['final-candidate-replay'][0]/'result.json').read_text())['cases']
assert len(rep)==500
for row in rep:
 i=int(row['seed']);assert 500<=i<1000 and len(row['order_scores'])==8
 assert row['order_scores'][0]==loaded[chosen][0][i]
out['replay_real_list_identical']=len(rep)
freeze=m['frozen']
import hashlib
assert hashlib.sha256((R/chosen/'src/main.cpp').read_bytes()).hexdigest()==freeze['sha256']
assert hashlib.sha256((N.parent/freeze['candidate']/'main.cpp').read_bytes()).hexdigest()==freeze['sha256']
(N/'final-stats.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'compare_fix':out['compare'][base],'timing':out['timing'],'paired':out['paired'],'p99':out['p99_paired_bootstrap']},indent=2))
