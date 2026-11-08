"""Lightweight provisional order-0 time summary from metrics.json, no solver executions."""
from pathlib import Path
import json,statistics,math,re,sys
R=Path('/home/sato/ahc074/runs')
rids=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',Path(sys.argv[1]).read_text(),re.M)
data=[]
for rid in rids:
 d=R/rid
 if not(d/'metrics.json').exists():raise SystemExit('metrics pending: '+rid)
 a=json.loads((d/'metrics.json').read_text())['cases'];a={int(k):v['stderr'] for k,v in a.items()}
 for v in a.values():v['judge_sec']=v['end_sec']+.04*v['helper_end_sec']+.35*v['req_sec']
 data.append(a)
ix=sorted(set.intersection(*[set(a) for a in data]));print('order0 only',len(ix))
for rid,a in zip(rids,data):
 print(rid)
 for key in ['helper_end_sec','req_sec','end_sec','judge_sec']:
  x=[a[i][key] for i in ix];diff=[1000*(a[i][key]-data[0][i][key]) for i in ix]
  x.sort();t=.99*(len(x)-1);lo=int(t);p99=x[lo]+(t-lo)*(x[min(lo+1,len(x)-1)]-x[lo])
  print(key,'mean',statistics.mean(x),'p99',p99,'paired_ms',statistics.mean(diff),statistics.stdev(diff)/math.sqrt(len(diff)))
