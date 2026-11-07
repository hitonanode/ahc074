"""Lightweight (<1 CPU second) summaries for already completed runs; no output replay."""
import sys,json,math
from pathlib import Path
R=Path('/home/sato/ahc074/runs')
def scores(run):
 return {int(x['seed']):x.get('order_scores',[x['score']]) for x in json.loads((R/run/'result.json').read_text())['cases'] if int(x['seed'])<500}
def mean(a):return sum(a)/len(a)
def se(a):
 m=mean(a);return (sum((x-m)**2 for x in a)/(len(a)-1)/len(a))**.5
ref=scores(sys.argv[1])
for run in sys.argv[2:]:
 try:
  c=scores(run);ids=sorted(set(ref)&set(c));out={}
  for name,sl in [('all',slice(None)),('real',slice(0,1)),('fresh',slice(1,None))]:
   if not ids or not c[ids[0]][sl] or not ref[ids[0]][sl]:continue
   if any(min(ref[i]+c[i])<=0 for i in ids):out['WA']=True;break
   v=[100*math.log(mean(c[i][sl])/mean(ref[i][sl])) for i in ids]
   out[name]=[mean(v),se(v)]
  p=R/run/'metrics.json'
  if p.exists():
   m=json.loads(p.read_text())['cases'];m=[v['stderr'] for k,v in m.items() if int(k)<500]
   out['time']={key:mean([v[key] for v in m]) for key in ['helper_end_sec','map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','req_sec'] if all(key in v for v in m)}
   if all('req_sec' in v for v in m):
    t=sorted(1.04*v['helper_end_sec']+1.35*v['req_sec']+v['end_sec']-v['helper_end_sec']-v['req_sec'] for v in m)
    ix=.99*(len(t)-1);lo=int(ix);q=t[lo]+(ix-lo)*(t[min(lo+1,len(t)-1)]-t[lo])
    out['judge']=[mean(t),q,max(t)]
  print(run,len(ids),json.dumps(out))
 except (OSError,ValueError,KeyError) as ex:print(run,str(ex))
