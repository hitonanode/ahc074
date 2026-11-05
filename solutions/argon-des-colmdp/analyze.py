"""Paired fixed-design comparisons, clustered by design seed. Run via whenidle and flock."""
import argparse,json,math,re,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');p.add_argument('--output',required=True);p.add_argument('--affected');a=p.parse_args()
root=Path('/home/sato/ahc074/runs')
def stat(v):return dict(mean=statistics.mean(v),se=statistics.stdev(v)/math.sqrt(len(v))if len(v)>1 else 0,min=min(v),max=max(v))
def quant(v,p):
 v=sorted(v);x=(len(v)-1)*p;i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
def read(name):return {c['seed']:c for c in json.loads((root/name/'result.json').read_text())['cases']}
base=read(a.runs[0]);out=[]
affected=set(x['seed']for x in json.loads(Path(a.affected).read_text())['rows'])if a.affected else set()
pattern=re.compile(r'^([a-zA-Z_]\w*) = ([-+\deE.]+)$',re.M)
allmetrics=[]
for name in a.runs:
 rows=read(name);seeds=sorted(set(rows)&set(base));diff=[];metrics={};judge=[];wa=0
 for seed in seeds:
  b=base[seed].get('order_scores',[base[seed]['score']]);c=rows[seed].get('order_scores',[rows[seed]['score']])
  assert len(b)==len(c)
  wa+=sum(x<=0 for x in c)
  diff.append(stat([100*math.log(y/x)for x,y in zip(b,c)])['mean'])
  for order in range(len(c)):
   folder=root/name if order==0 else root/name/'orders'/str(order)
   e={k:float(v)for k,v in pattern.findall((folder/'err'/f'{seed:04d}.txt').read_text())}
   metrics[(seed,order)]=e
   judge.append(e['end_sec']+.04*e['helper_end_sec']+.35*e['req_sec'])
 keys=set.intersection(*(set(e)for e in metrics.values()))
 keep=[k for k in keys if k.startswith(('colmdp_','d3_','d4_','d5_'))or k in ['req_sec','helper_end_sec','end_sec','self_wrong','op_label_errors','generic_moves','total_moves']]
 if not allmetrics:baseline=metrics
 result=dict(run=name,n=len(seeds),orders=len(c),wa=wa,score=stat(diff),wtl=[sum(d<-1e-12 for d in diff),sum(abs(d)<=1e-12 for d in diff),sum(d>1e-12 for d in diff)],metrics={},deltas={},judge=dict(**stat(judge),p99=quant(judge,.99),over2=sum(x>2 for x in judge)))
 for key in sorted(keep):
  result['metrics'][key]=stat([e[key]for e in metrics.values()])
  if all(key in baseline[s]for s in metrics):result['deltas'][key]=stat([e[key]-baseline[s][key]for s,e in metrics.items()])
 if affected:
  for key,select in [('affected',affected),('unaffected',set(seeds)-affected)]:
   v=[x for s,x in zip(seeds,diff)if s in select]
   result[key]=dict(n=len(v),score=stat(v),wtl=[sum(d<-1e-12 for d in v),sum(abs(d)<=1e-12 for d in v),sum(d>1e-12 for d in v)])
 allmetrics.append(metrics);out.append(result)
 print(name,result['score'],result['wtl'],result.get('affected',''),flush=True)
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
