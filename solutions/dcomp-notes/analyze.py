"""Paired seed-level replay/normal differences and stage/repair diagnostics.
Positive differences mean more moves (worse). Trace analysis uses flock + nice;
--scores-only reads the small result JSONs without scanning request traces.
"""
from pathlib import Path
import argparse,json,math,re,statistics,collections
R=Path('/home/sato/ahc074/runs')
def mean(a):return statistics.mean(a) if len(a) else None
def se(a):return statistics.stdev(a)/math.sqrt(len(a)) if len(a)>1 else 0
p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('runs',nargs='+');p.add_argument('--output');p.add_argument('--scores-only',action='store_true');a=p.parse_args()
def read(name):
 d=Path(name) if Path(name).is_dir() else R/name
 meta=json.loads((d/'meta.json').read_text());assert meta['status']=='ok',(name,meta['status'])
 cases={int(c['seed']):c for c in json.loads((d/'result.json').read_text())['cases']}
 assert all(c['score']>0 for c in cases.values())
 return d,cases,meta
rd,ref,rm=read(a.reference);out={}
for run in a.runs:
 d,cases,meta=read(run);ss=sorted(set(ref)&set(cases));z={'n':len(ss),'ref':a.reference,'score':{},'stage':{},'diag':{},'outside_load':meta.get('outside_load')}
 for label,start,end in [('fresh',1,8),('all',0,8),('real',0,1)]:
  dif=[];ratio=[];order_ratio=[]
  for i in ss:
   b=ref[i].get('order_scores',[ref[i]['score']])[start:end];c=cases[i].get('order_scores',[cases[i]['score']])[start:end]
   if not b or not c:continue
   assert len(b)==len(c) and min(b+c)>0
   x,y=mean(b),mean(c);dif.append((y-x)/1024);ratio.append(100*math.log(y/x))
   order_ratio.append(mean([100*math.log(y/x) for x,y in zip(b,c)]))
  if dif:z['score'][label]={'moves':mean(dif),'moves_se':se(dif),'pct':mean(ratio),'pct_se':se(ratio),'pct_orders':mean(order_ratio),'pct_orders_se':se(order_ratio),'wtl':[sum(x<0 for x in dif),sum(x==0 for x in dif),sum(x>0 for x in dif)]}
 if a.scores_only:out[run]=z;continue
 numeric=collections.defaultdict(list);reference_numeric=collections.defaultdict(list);steps=[];failures=[];failure_count=0
 for i in ss:
  t=(d/'err'/f'{i:04d}.txt').read_text()
  values={k:float(v) for k,v in re.findall(r'^([a-zA-Z][a-zA-Z0-9_]*) = ([-+0-9.eE]+)$',t,re.M)}
  for k,v in values.items():numeric[k].append(v)
  reference_text=(rd/'err'/f'{i:04d}.txt').read_text()
  reference_values={k:float(v) for k,v in re.findall(r'^([a-zA-Z][a-zA-Z0-9_]*) = ([-+0-9.eE]+)$',reference_text,re.M)}
  for k,v in reference_values.items():reference_numeric[k].append(v)
  for line in t.splitlines():
   if line.startswith('@lns_step '):steps.append([float(v) for v in line.split()[1:]])
   elif line.startswith('@lns_failure '):
    failure_count+=1
    try:failures.append([float(v) for v in line.split()[1:]])
    except ValueError:pass
 for k in ['map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','helper_end_sec','req_sec','end_sec','lns_sec','lns_map_sec','lns_repair_sec','lns_gain_v','lns_improved','lns_success','dv_candidates']:
  if k in numeric:
   z['stage'][k]={'mean':mean(numeric[k]),'se':se(numeric[k]),'max':max(numeric[k])}
   if len(reference_numeric.get(k,[]))==len(numeric[k]):
    changes=[x-y for x,y in zip(numeric[k],reference_numeric[k])]
    refmean=mean(reference_numeric[k]);z['stage'][k].update(reference_mean=refmean,ratio=mean(numeric[k])/refmean if refmean else None,paired_delta=mean(changes),paired_delta_se=se(changes))
 z['chosen']=dict(collections.Counter(numeric.get('dv_chosen',[])))
 if steps:
  names=['step','mode','sheet','windows','destroyed','broken','free_targets','released_pairs','expanded','new_repair','new_anneal','new_finish','parent_model','raw_model','annealed_model','parent_raw_v','raw_v','parent_v','v','better','map_before','map_after','sec','max_old_loss','max_accepted_old_loss','tracked_old_pairs','window_changes','graph_added','graph_removed']
  z['diag']={k:mean([s[i] for s in steps if i<len(s)]) for i,k in enumerate(names) if any(i<len(s) for s in steps)}
  z['diag']['n']=len(steps);z['diag']['raw_v_better']=mean([s[16]<s[15] for s in steps]);z['diag']['model_better']=mean([s[14]<s[12] for s in steps])
  z['diag']['attempts']=len(steps)+failure_count;z['diag']['repair_failures']=failure_count
  z['diag']['destroyed_all_attempts']=mean([s[4] for s in steps]+[f[1] for f in failures if len(f)>=4])
  z['diag']['broken_after_map_all_attempts']=mean([s[5] for s in steps]+[f[2] for f in failures if len(f)>=4])
  z['diag']['full_graph_matching_failures']=sum(f[3]==2 for f in failures if len(f)>=4)
  z['diag']['expanded_successful_steps']=sum(s[8]>0 for s in steps)
  z['diag']['expanded_and_V_better_steps']=sum(s[8]>0 and s[19]>0 for s in steps)
  z['diag']['regional_and_V_better_steps']=sum(s[8]==0 and s[19]>0 for s in steps)
  if all(len(s)>26 for s in steps):
   z['diag']['window_change_fraction_successful']=mean([s[26]>0 for s in steps])
   z['diag']['better_and_changed_windows']=sum(s[26]>0 and s[19]>0 for s in steps)
 out[run]=z
s=json.dumps(out,indent=2);print(s)
if a.output:Path(a.output).write_text(s+'\n')
