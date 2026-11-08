"""Task13 normal comparison and deadline diagnostics, under flock + nice."""
from pathlib import Path
import argparse,json,re,hashlib,math,collections
import numpy as np
p=argparse.ArgumentParser();p.add_argument('runs',nargs=4);p.add_argument('--count',type=int,default=2000);p.add_argument('--output',required=True);a=p.parse_args()
R=Path('/home/sato/ahc074/runs');N=Path(__file__).resolve().parent
rx=re.compile(r'^([A-Za-z][A-Za-z0-9_]*) = ([-+0-9.eE]+)$',re.M)
def st(values):
 x=np.asarray(values,float)
 return {'n':len(x),'mean':float(x.mean()),'se':float(x.std(ddof=1)/math.sqrt(len(x))),
         'min':float(x.min()),'p01':float(np.percentile(x,1)),'p50':float(np.percentile(x,50)),
         'p95':float(np.percentile(x,95)),'p99':float(np.percentile(x,99)),
         'p999':float(np.percentile(x,99.9)),'max':float(x.max())}
def read(rid):
 d=R/rid;m=json.loads((d/'meta.json').read_text());assert m['status']=='ok'
 cs=sorted(json.loads((d/'result.json').read_text())['cases'],key=lambda c:int(c['seed']))
 assert [int(c['seed'])for c in cs]==list(range(a.count));assert all(c['score']>0 for c in cs)
 rows=[]
 for seed in range(a.count):
  q={k:float(v)for k,v in rx.findall((d/'err'/f'{seed:04d}.txt').read_text())}
  q['judge_old_sec']=q['end_sec']+.04*q['helper_end_sec']+.35*q['req_sec']
  q['judge_req25_sec']=q['end_sec']+.25*q['req_sec']
  q['rest_sec']=q['end_sec']-q['helper_end_sec']-q['req_sec']
  rows.append(q)
 return np.asarray([c['score']for c in cs]),rows,m
loaded={r:read(r)for r in a.runs};argon,base,*candidates=a.runs
out={'runs':a.runs,'count':a.count,'scores':{},'times':{},'paired':{},'deadline':{},'meta':{}}
for rid,(scores,rows,m)in loaded.items():
 out['times'][rid]={k:st([q[k]for q in rows])for k in ['helper_end_sec','req_sec','end_sec','rest_sec','judge_old_sec','judge_req25_sec']}
 out['times'][rid]['end_above']={str(t):sum(q['end_sec']>t for q in rows)for t in [1.8,1.85,1.9,1.93,2.]}
 out['times'][rid]['old_ratio_argon']=out['times'][rid]['judge_old_sec']['mean']/np.mean([q['judge_old_sec']for q in loaded[argon][1]])
 out['meta'][rid]={'record':m['record'],'outside_load':m.get('outside_load'),'summary':m.get('summary'),
                  'command':m['compile_command'],'sha256':hashlib.sha256((R/rid/'src/main.cpp').read_bytes()).hexdigest()}
for rid in candidates:
 scores,rows,m=loaded[rid];bs,brows,_=loaded[base];delta=100*np.log(scores/bs)
 groups=[('all',0,a.count),('0-999',0,min(1000,a.count))]
 if a.count>1000:groups += [('1000-1999',1000,a.count),('500-1999',500,a.count)]
 out['scores'][rid]={}
 for label,lo,hi in groups:
  d=scores[lo:hi]-bs[lo:hi]
  out['scores'][rid][label]={'pct':st(delta[lo:hi]),'moves':st(d/1024),'wtl':[int(sum(d<0)),int(sum(d==0)),int(sum(d>0))]}
 out['paired'][rid]={k:st([q[k]-b[k]for q,b in zip(rows,brows)])for k in ['helper_end_sec','req_sec','end_sec','judge_old_sec','judge_req25_sec']}
 assert all(q['dv_candidates']==9 and q['design_time_enabled']==1 for q in rows)
 phases=[v['name']for v in json.loads((N/'t13-shares.json').read_text())['schedule']]
 timed=[k for k in phases if k in ['map_search','gopt']or'anneal_'in k or k.endswith('_filler')]
 fractions={v['name']:v['cumulative']for v in json.loads((N/'t13-shares.json').read_text())['schedule']}
 dt={'phase':{},'budget':st([q['design_time_budget_sec']for q in rows]),
     'helper_minus_budget_end':st([q['helper_end_sec']-q['design_time_end_sec']for q in rows]),
     'clock_reads':st([q['design_clock_reads']for q in rows]),'chosen':dict(collections.Counter(int(q['dv_chosen'])for q in rows))}
 for k in phases:
  v={'seconds':st([q[f'dt_{k}_sec']for q in rows])}
  if k in timed:
   counts=[q[f'dt_{k}_iters']for q in rows]
   v['iterations']=st(counts);v['zero_count']=sum(n==0 for n in counts)
   v['deadline_overrun']=st([q[f'dt_{k}_end']-q['design_time_start_sec']-q['design_time_budget_sec']*fractions[k]for q in rows])
  dt['phase'][k]=v
 out['deadline'][rid]=dt
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
for rid in candidates:
 v=out['scores'][rid]['all'];print(rid,'vs',base,v['pct']['mean'],v['pct']['se'],v['wtl'])
 for k in ['helper_end_sec','req_sec','end_sec']:print(k,out['times'][rid][k], 'paired',out['paired'][rid][k])
 print('zero iterations',{k:v['zero_count']for k,v in out['deadline'][rid]['phase'].items()if v.get('zero_count',0)})
