from pathlib import Path
import argparse,json,re,math,statistics
p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');p.add_argument('--output',required=True);p.add_argument('--identity',action='store_true');a=p.parse_args()
root=Path('/home/sato/ahc074/runs');rx=re.compile(r'^([A-Za-z][A-Za-z0-9_]*) = ([-+0-9.eE]+)$',re.M)
def stat(v):
 v=sorted(v);q=(len(v)-1)*.99;i=int(q)
 return {'n':len(v),'mean':statistics.mean(v),'se':statistics.stdev(v)/math.sqrt(len(v)) if len(v)>1 else 0,'p99':v[i]+(q-i)*(v[min(i+1,len(v)-1)]-v[i]),'min':v[0],'max':v[-1]}
def load(r):
 d=root/r;m=json.loads((d/'meta.json').read_text());c={int(x['seed']):x for x in json.loads((d/'result.json').read_text())['cases']};logs={}
 for i,x in c.items():
  ls=[]
  for j in range(len(x.get('order_scores') or [x['score']])):
   dd=d if j==0 else d/'orders'/str(j)
   ls.append(dict((k,float(v)) for k,v in rx.findall((dd/'err'/f'{i:04d}.txt').read_text())))
  keys=set.intersection(*(set(l) for l in ls));logs[i]={k:statistics.mean(l[k] for l in ls) for k in keys};logs[i]['_samples']=ls
 return d,m,c,logs
b,bm,bc,bl=load(a.runs[0]);out={'base':a.runs[0],'comparisons':{}}
for r in a.runs[1:]:
 d,m,c,l=load(r);ss=sorted(c.keys()&bc.keys());good=[];ratios=[]
 for i in ss:
  x=c[i].get('order_scores') or [c[i]['score']];y=bc[i].get('order_scores') or [bc[i]['score']]
  assert len(x)==len(y)
  if min(x+y)>0:good.append(i);ratios.append(statistics.mean(math.log(u/v)*100 for u,v in zip(x,y)))
 z={'n':len(ss),'wa':len(ss)-len(good),'score':stat(ratios),'wtl':[sum(x<0 for x in ratios),sum(x==0 for x in ratios),sum(x>0 for x in ratios)],'paired_ms':{},'arm_p99_ms':{},'counters':{},'paired_metrics':{},'outside_load':m.get('outside_load')}
 if a.identity:
  identical=0;design_identical=0;annotations_identical=0
  for i in ss:
   same=True;annotations_same=True
   for j in range(len(c[i].get('order_scores') or [c[i]['score']])):
    dd=d if j==0 else d/'orders'/str(j);bb=b if j==0 else b/'orders'/str(j)
    same &= (dd/'out'/f'{i:04d}.txt').read_bytes()==(bb/'out'/f'{i:04d}.txt').read_bytes()
    def annotations(path):return [line for line in path.read_text().splitlines() if line.startswith(('@paper ','@ops '))]
    annotations_same &= annotations(dd/'err'/f'{i:04d}.txt')==annotations(bb/'err'/f'{i:04d}.txt')
   identical+=same;annotations_identical+=annotations_same
   design_identical+=((d/'out'/f'{i:04d}.txt').read_bytes().splitlines()[:192]==(b/'out'/f'{i:04d}.txt').read_bytes().splitlines()[:192])
  z['stdout_identical']=identical;z['design_identical']=design_identical;z['annotations_identical']=annotations_identical
 for k in ['map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','helper_end_sec','req_sec','end_sec']:
  if all(k in l[i] and k in bl[i] for i in ss):
   z['paired_ms'][k]=stat([1000*(l[i][k]-bl[i][k]) for i in ss]);z['arm_p99_ms'][k]=[stat([1000*x[k] for i in ss for x in bl[i]['_samples']])['p99'],stat([1000*x[k] for i in ss for x in l[i]['_samples']])['p99']]
 for k in ['dv_best','dv_first','model_cost','model_col','model_hole','model_gc','proxy_after','perforation_holes']:
  if all(k in l[i] and k in bl[i] for i in ss):z['paired_metrics'][k]=stat([l[i][k]-bl[i][k] for i in ss])
 keys=set.union(*(set(l[i]) for i in ss))
 z['request_work']={}
 for k in ['colmdp_full_states','colmdp_sequences','complete_value_plans','value_filler_plans','partial_mdp_hits','partial_mdp_misses','tie_decisions','tie_switches','screen_prepared','screen_skipped','eject_trials','neutral_total','neutral_accepted','ns_plan_calls','f2_memo_hits','f2_memo_misses','f2_prefix_steps','f2_replay_steps','post_candidate_calls','rewrite_trials']:
  if all(k in l[i] and k in bl[i] for i in ss):
   z['request_work'][k]={'base':statistics.mean(bl[i][k] for i in ss),'candidate':statistics.mean(l[i][k] for i in ss),'paired':stat([l[i][k]-bl[i][k] for i in ss])}
 for k in sorted(keys):
  if k.startswith(('map_alt_','dv_','tie_','helper_menu_','f2_plan_','interleave_')):z['counters'][k]=stat([l[i][k] for i in ss if k in l[i]])
 if all(k in z['paired_ms'] for k in ['helper_end_sec','req_sec']):
  # Positive is the required score benefit; saved time is a credit.
  z['time_charge_pct']=.0003*z['paired_ms']['helper_end_sec']['mean']+.00055*z['paired_ms']['req_sec']['mean']
  z['net_log_ratio_pct']=z['score']['mean']+z['time_charge_pct']
  z['net_score']=stat([ratio+.3*(l[i]['helper_end_sec']-bl[i]['helper_end_sec'])+.55*(l[i]['req_sec']-bl[i]['req_sec']) for i,ratio in zip(good,ratios)])
 out['comparisons'][r]=z
 print(r,'n',z['n'],'score',z['score']['mean'],z['score']['se'],'WTL',z['wtl'],'WA',z['wa'],'identity',z.get('stdout_identical'))
 print('paired ms',{k:(round(v['mean'],3),round(v['se'],3)) for k,v in z['paired_ms'].items()})
 print('p99 ms',z['arm_p99_ms'])
 print('counters',{k:round(v['mean'],5) for k,v in z['counters'].items() if k.startswith(('map_alt_','helper_menu_'))})
 print('charge/net',z.get('time_charge_pct'),z.get('net_log_ratio_pct'))
 print('paired metrics',{k:(v['mean'],v['se']) for k,v in z['paired_metrics'].items()})
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
