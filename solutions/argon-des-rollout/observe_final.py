"""Saved-output diagnosis. Launch with whenidle and exclusive runs/.lock."""
import collections,json,math,subprocess,sys
from pathlib import Path
here=Path(__file__).resolve().parent;runs=Path('/home/sato/ahc074/runs')
base='20261106-073713_argon-des-perf-latew105';cand='20261106-073713_argon-des-rollout-s16'
def cases(run):return {c['seed']:c for c in json.loads((runs/run/'result.json').read_text())['cases']}
b,c=cases(base),cases(cand)
worst=sorted(b,key=lambda s:c[s]['score']-b[s]['score'],reverse=True)[:2]
def labels(run,seed):
 out={}
 for line in (runs/run/'err'/f'{seed:04d}.txt').read_text().splitlines():
  if not line.startswith('@ops '):continue
  q=int(line.split()[1]);counts=collections.Counter()
  for x in line.split('=',1)[1].split():
   name,sep,n=x.partition('*');counts[name]+=int(n)if sep else 1
  out[q]=counts
 return out
with (here/'observe-final.log').open('w')as log:
 subprocess.run([sys.executable,'scripts/observe.py','cases',cand,'--vs',base,'--top','3'],stdout=log,stderr=log,check=True)
 for seed in worst:
  x,y=labels(base,seed),labels(cand,seed)
  qs=sorted(x,key=lambda q:sum(y[q].values())-sum(x[q].values()),reverse=True)[:2]
  for q in qs:
   print('\nCASE',seed,'REQUEST',q,'BASE',dict(x[q]),'S16',dict(y[q]),file=log,flush=True)
   for run in [base,cand]:
    subprocess.run([sys.executable,'scripts/observe.py','queries',run,str(seed),'--from',str(q),'--to',str(q+1),'--attr','role,col'],stdout=log,stderr=log,check=True)
 print('\nOperation labels across the first order sequence:',file=log)
 totals=[]
 for run in [base,cand]:
  counts=collections.Counter()
  for seed in b:
   for v in labels(run,seed).values():counts.update(v)
  totals.append(counts)
  print(run,{k:v/(100*1024)for k,v in sorted(counts.items())},file=log)
 print('delta',{k:(totals[1][k]-totals[0][k])/(100*1024)for k in sorted(set(totals[0])|set(totals[1]))},file=log)
