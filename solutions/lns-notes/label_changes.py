"""Audit E=0 through trace move totals and paired fresh-list label changes.
Run under the shared flock with nice. The labels describe generation paths,
not a causal decomposition of cost.
"""
from pathlib import Path
import argparse,json,statistics,re,math,collections
R=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('--output',required=True);a=p.parse_args()
def read(run):
 d=R/run;assert json.loads((d/'meta.json').read_text())['status']=='ok'
 return d,{c['seed']:c for c in json.loads((d/'result.json').read_text())['cases']}
b,bc=read(a.base);c,cc=read(a.candidate);seeds=sorted(set(bc)&set(cc));assert seeds
bad=['self_wrong','op_label_errors','plan_failures','unsafe_plans']
def counts(root,seed,order,score):
 path=root/f'orders/{order}/err/{seed:04d}.txt';out=collections.Counter();seen=0;errors={}
 with path.open() as f:
  for line in f:
   if line.startswith('@ops '):
    seen+=1
    for token in line.partition('=')[2].split():
     name,sep,n=token.partition('*');out[name]+=int(n) if sep else 1
   else:
    name,sep,v=line.partition(' = ')
    if name in bad:errors[name]=int(float(v))
 assert seen==1024 and sum(out.values())==score,(path,seen,sum(out.values()),score)
 assert all(errors.get(k)==0 for k in bad),(path,errors)
 return out
rows=[];base_rows=[];candidate_rows=[]
for seed in seeds:
 x=collections.Counter();y=collections.Counter()
 for order in range(1,8):x.update(counts(b,seed,order,bc[seed]['order_scores'][order]));y.update(counts(c,seed,order,cc[seed]['order_scores'][order]))
 base_rows.append(x);candidate_rows.append(y);rows.append({k:(y[k]-x[k])/(7*1024) for k in x.keys()|y.keys()})
keys=set().union(*(r.keys() for r in rows))
def stat(v):return {'mean':statistics.mean(v),'se':statistics.stdev(v)/len(v)**.5}
out={'n':len(seeds),'lists':'1-7','all_trace_moves_equal_scores':True,'request_count':len(seeds)*7*1024,'delta':{},'base':{},'candidate':{}}
for k in sorted(keys):
 out['delta'][k]=stat([r.get(k,0) for r in rows]);out['base'][k]=statistics.mean([r[k]/(7*1024) for r in base_rows]);out['candidate'][k]=statistics.mean([r[k]/(7*1024) for r in candidate_rows])
for k,group in [('handle_related',['fix','fill','fdig','fret','relevel','reuse']),('generic_related',['gen','help','hdig']),('total',list(keys))]:out['delta'][k]=stat([sum(r.get(s,0) for s in group) for r in rows])
Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
