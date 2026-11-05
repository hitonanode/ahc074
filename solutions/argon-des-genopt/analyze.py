"""Summarize stored metrics; invoke through the supplied whenidle.sh wrapper."""
import argparse, json, math, statistics
from pathlib import Path

here=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');p.add_argument('--output',default='summary.json')
p.add_argument('--identity-base');a=p.parse_args()
root=Path('/home/sato/ahc074/runs')
def stats(v):
 return {'mean':statistics.mean(v),'se':statistics.stdev(v)/math.sqrt(len(v)) if len(v)>1 else 0,
         'min':min(v),'max':max(v)}
def quantile(v,q):
 s=sorted(v);x=(len(s)-1)*q;i=int(x);return s[i]+(s[min(i+1,len(s)-1)]-s[i])*(x-i)
base=None;out=[]
for name in a.runs:
 cases=json.loads((root/name/'metrics.json').read_text())['cases']
 seeds=sorted(cases,key=int);r={'run':name,'n':len(seeds),'metrics':{}}
 if base is None:base=cases
 score=[100*math.log(cases[s]['score']/base[s]['score'])for s in seeds if cases[s]['score'] and base[s]['score']]
 r.update(score=stats(score),wins=sum(cases[s]['score']<base[s]['score']for s in seeds),
          ties=sum(cases[s]['score']==base[s]['score']for s in seeds),losses=sum(cases[s]['score']>base[s]['score']for s in seeds))
 keys=sorted(set.intersection(*(set(cases[s]['stderr'])for s in seeds)))
 for k in keys:
  if not (k.startswith('d1_') or k.startswith('model_') or k.endswith('_sec') or k in ['self_wrong','op_label_errors']):continue
  vals=[cases[s]['stderr'][k] for s in seeds]
  r['metrics'][k]=stats(vals)
  r['metrics'][k]['nonzero']=sum(v!=0 for v in vals)
  if all(k in base[s]['stderr'] for s in seeds):
   r['metrics'][k]['delta']=stats([cases[s]['stderr'][k]-base[s]['stderr'][k] for s in seeds])
 judge=[]
 for s in seeds:
  m=cases[s]['stderr'];judge.append(m['end_sec']+.04*m['helper_end_sec']+.35*m['req_sec'])
 r['judge']={**stats(judge),'p99':quantile(judge,.99),'over_2':sum(x>2 for x in judge)}
 r['wa']=sum(not cases[s]['score'] for s in seeds)
 if a.identity_base:
  ref=root/a.identity_base
  r['stdout_identical']=sum((root/name/'out'/f'{int(s):04d}.txt').read_bytes()==(ref/'out'/f'{int(s):04d}.txt').read_bytes()for s in seeds)
 r['rows']={s:{k:v for k,v in cases[s]['stderr'].items() if k.startswith('d1_')}for s in seeds}
 out.append(r)
(here/a.output).write_text(json.dumps(out,indent=2)+'\n')
for r in out:
 print(r['run'],r['score'],r['judge'])
 for k,v in r['metrics'].items():
  if k.startswith('d1_'):print(k,v['mean'],v['min'],v['max'],v['nonzero'])
