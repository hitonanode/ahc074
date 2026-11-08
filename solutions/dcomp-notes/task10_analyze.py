"""Run under flock+nice. Per-seed averaging for paired multi-order timings and identity."""
from pathlib import Path
import argparse,json,math,re
import numpy as np
p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('reference');p.add_argument('candidates',nargs='+');p.add_argument('--seeds',default='0-200');p.add_argument('--orders',type=int,default=4);a=p.parse_args()
r=Path('/home/sato/ahc074/runs');dest=Path(__file__).resolve().parent;lo,hi=map(int,a.seeds.split('-'));rx=re.compile(r'^([a-zA-Z][a-zA-Z0-9_]*) = ([-+0-9.eE]+)$',re.M)
def stats(v):
 v=np.array(v,float);return {'mean':float(v.mean()),'se':float(v.std(ddof=1)/math.sqrt(len(v))) if len(v)>1 else 0,'p99':float(np.percentile(v,99)),'max':float(v.max())}
def read(name):
 d=r/name;m=json.loads((d/'meta.json').read_text());assert m['status']=='ok',name
 cs={int(c['seed']):c for c in json.loads((d/'result.json').read_text())['cases']};scores=[];rows=[];outputs=[]
 for seed in range(lo,hi):
  ss=cs[seed].get('order_scores',[cs[seed]['score']]);assert len(ss)>=a.orders and min(ss)>0;scores.append(ss[:a.orders]);row=[];outs=[]
  for j in range(a.orders):
   sub=d if j==0 else d/'orders'/str(j);t=(sub/'err'/f'{seed:04d}.txt').read_text();v={k:float(x) for k,x in rx.findall(t)}
   if 'helper_end_sec' in v:v['judge_sec']=v['end_sec']+.04*v['helper_end_sec']+.35*v['req_sec']
   row.append(v);outs.append((sub/'out'/f'{seed:04d}.txt').read_bytes())
  keys=set.intersection(*(set(x) for x in row));rows.append({k:sum(v[k] for v in row)/a.orders for k in keys});outputs.append(outs)
 return np.array(scores),rows,outputs,m
b,br,bo,bm=read(a.reference);allr={}
for name in a.candidates:
 c,cr,co,cm=read(name);delta=100*np.log(c/b).mean(axis=1);dif=[]
 for si in range(hi-lo):
  for j in range(a.orders):
   if bo[si][j]!=co[si][j]:dif.append([si+lo,j])
 v={'score_pct':stats(delta),'wtl':[int(sum(delta<0)),int(sum(delta==0)),int(sum(delta>0))],'identity':{'same':(hi-lo)*a.orders-len(dif),'total':(hi-lo)*a.orders,'different':dif},'metrics':{}}
 keys=set.intersection(*(set(x) for x in cr))
 for k in sorted(keys):
  if k.endswith('_sec') or k.startswith(('cfprof_','dp_','dprof_','screen_','cf_value','f2_memo_')):
   x=np.array([z[k] for z in cr]);v['metrics'][k]={'candidate':stats(x)}
   if all(k in z for z in br):
    y=np.array([z[k] for z in br]);v['metrics'][k].update(reference=stats(y),paired=stats(x-y))
 allr[name]=v
 print(name, 'score',v['score_pct'],'WTL',v['wtl'],'identity',v['identity']['same'],'/',v['identity']['total'])
 for k in ('helper_end_sec','req_sec','end_sec','judge_sec'):
  if k in v['metrics']:print(k,v['metrics'][k]['paired'])
(dest/(a.tag+'.json')).write_text(json.dumps({'reference':a.reference,'seeds':[lo,hi],'orders':a.orders,'results':allr},indent=2)+'\n')
