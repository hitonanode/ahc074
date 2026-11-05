#!/usr/bin/env python3
"""Read saved evaluation artifacts. Does not execute solutions or testers."""
from pathlib import Path
import argparse,json,math,re,statistics as st
p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=2000);p.add_argument('--json',dest='output');a=p.parse_args()
root=Path('/home/sato/ahc074/runs');metric=re.compile(r'^([\w]+) = ([-+\d.eE]+)$',re.M)
def quantile(xs,q):
 ys=sorted(xs);pos=(len(ys)-1)*q;i=int(pos);return ys[i]+(ys[min(i+1,len(ys)-1)]-ys[i])*(pos-i)
def read(name):
 r=root/name;cases={v['seed']:v for v in json.loads((r/'result.json').read_text())['cases'] if a.start<=v['seed']<a.end};logs={}
 for seed,c in cases.items():
  for j in range(len(c.get('order_scores',[c['score']]))):
   f=(r if j==0 else r/'orders'/str(j))/'err'/f'{seed:04d}.txt'
   logs[seed,j]={k:float(v) for k,v in metric.findall(f.read_text())}
 return cases,logs
all_results={};bc,bl=read(a.runs[0])
for name in a.runs:
 cc,ll=read(name);seeds=sorted(bc.keys()&cc.keys());pairs=sorted(k for k in bl.keys()&ll.keys() if k[0] in seeds)
 changes=[];wa=0
 for s in seeds:
  av=bc[s].get('order_scores',[bc[s]['score']]);bv=cc[s].get('order_scores',[cc[s]['score']]);wa+=sum(x<=0 for x in bv)
  ds=[math.log(y/x) for x,y in zip(av,bv) if x>0 and y>0]
  if ds:changes.append(100*sum(ds)/len(ds))
 def mean(logs,key):return st.mean(logs[k][key] for k in pairs if key in logs[k])
 result={'seeds':len(seeds),'cases':len(pairs),'score_log_pct':st.mean(changes),'se_pct':st.stdev(changes)/math.sqrt(len(changes)) if len(changes)>1 else 0,'wtl':[sum(x<0 for x in changes),sum(x==0 for x in changes),sum(x>0 for x in changes)],'WA':wa,'means':{},'baseline_means':{},'judge':{},'baseline_judge':{}}
 fields=['map_end_sec','anneal_end_sec','climb_end_sec','match_end_sec','perforation_end_sec','helper_end_sec','req_sec','end_sec','gobj_after','model_cost','model_col','model_hole','model_gc','proxy_after','total_moves','generic_moves','self_wrong','op_label_errors','anneal_iters','map_iters','gopt_steps','climb_iters','match_iterations','ns_rounds','ns_plan_calls','post_candidate_calls']
 for key in fields:
  if key in ll[pairs[0]] and key in bl[pairs[0]]:result['means'][key]=mean(ll,key);result['baseline_means'][key]=mean(bl,key)
 for key,logs in [('judge',ll),('baseline_judge',bl)]:
  v=[logs[k]['end_sec']+.04*logs[k]['helper_end_sec']+.35*logs[k]['req_sec'] for k in pairs]
  result[key]={'mean':st.mean(v),'p99':quantile(v,.99),'max':max(v),'over2':sum(t>2 for t in v)}
  vv=[logs[k]['end_sec'] for k in pairs];result[key]['local_end']={'mean':st.mean(vv),'p99':quantile(vv,.99),'max':max(vv),'over2':sum(t>2 for t in vv)}
 result['req_ratio']=result['means']['req_sec']/result['baseline_means']['req_sec'];result['judge_mean_delta']=result['judge']['mean']-result['baseline_judge']['mean'];result['judge_p99_delta']=result['judge']['p99']-result['baseline_judge']['p99']
 all_results[name]=result
 print(name,'seeds',result['seeds'],'cases',result['cases'],'log%',result['score_log_pct'],'SE',result['se_pct'],'W/T/L',result['wtl'],'WA',wa)
 print('req',result['baseline_means']['req_sec'],'->',result['means']['req_sec'],'ratio',result['req_ratio'])
 print('judge mean/p99/max',*[result['baseline_judge'][k] for k in ['mean','p99','max']],'->',*[result['judge'][k] for k in ['mean','p99','max']],'over2',result['baseline_judge']['over2'],'->',result['judge']['over2'])
 print('stages',{k:round(v,6) for k,v in result['means'].items() if k.endswith('_end_sec')});print('models',{k:round(result['means'][k],6) for k in ['gobj_after','model_cost','proxy_after','self_wrong','op_label_errors']})
if a.output:Path(a.output).write_text(json.dumps(all_results,indent=2)+'\n')
