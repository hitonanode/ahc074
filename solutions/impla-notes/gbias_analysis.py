"""Read recorded comparisons and the handle color bias in saved designs; run under flock."""
import argparse,json,re,sys,math
from pathlib import Path
sys.dont_write_bytecode=True
import analyze as shared
notes=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('suite');p.add_argument('--end',type=int);p.add_argument('--arms',type=int,nargs='+');a=p.parse_args()
ids=re.findall(r'\[pahcer_run\] run-id: (\S+)',(notes/f'gbias-{a.suite}.log').read_text())
if a.arms:ids=[ids[0]]+[ids[i]for i in a.arms]
extra=['gbias_lambda','gbias_before','gbias_after','gobj_bias_before','gobj_bias_after','handle_minority_after','model_cost','model_col','model_hole','model_gc']
shared.KEYS+=extra;shared.PATTERN=re.compile(r'^('+'|'.join(shared.KEYS)+r') = ([\d.eE+\-]+)$',re.M)
out=[shared.compare(ids[0],rid,a.end)for rid in ids[1:]]
if a.suite=='smoke':
 for x in out:
  d=[s for s in range(20)if(shared.RUNS/x['base']/'out'/f'{s:04d}.txt').read_bytes()!=(shared.RUNS/x['candidate']/'out'/f'{s:04d}.txt').read_bytes()]
  x['stdout_different']=d
else:
 import importlib.util
 root=notes.parents[1]
 spec=importlib.util.spec_from_file_location('gbias_pahcer',root/'scripts/pahcer_run.py')
 runner=importlib.util.module_from_spec(spec);sys.modules[spec.name]=runner;spec.loader.exec_module(runner)
 cases=json.loads((shared.RUNS/ids[0]/'result.json').read_text())['cases']
 names={int(c['seed']):runner.barcode_hash(root/'tools/in'/f"{int(c['seed']):04d}.txt")+'.txt'for c in cases if a.end is None or int(c['seed'])<a.end}
 def biases(rid):
  rows={}
  for seed,name in names.items():
   path=shared.RUNS/rid/'design'/name
   fields={}
   for line in path.read_text().splitlines():
    name,_,value=line.partition(' ')
    if name=='stderr':break
    fields[name]=list(map(int,value.split())) if name not in ['end_sec'] else value
   assert fields['G']==[38] and fields['H']==[25],(rid,seed,'fallback design needs separate gobj accounting')
   handles=fields['handle'][1:];barcodes=fields['A'][1:];n=len(barcodes)
   ones=[sum((t>>h)&1 for t in barcodes)for h in handles]
   rows[seed]=[sum((v-128)**2 for v in ones)/len(ones),sum(min(v,n-v)/n for v in ones)/len(ones)]
  return rows
 baseline=biases(ids[0])
 base_cases,base_metrics,_=shared.load(ids[0],a.end)
 for x in out:
  candidate=biases(x['candidate']);seeds=sorted(baseline.keys()&candidate.keys());assert len(seeds)==x['n']
  candidate_cases,candidate_metrics,_=shared.load(x['candidate'],a.end)
  net=[100*math.log(candidate_cases[s]['score']/base_cases[s]['score'])+.3*(candidate_metrics[s]['helper_end_sec']-base_metrics[s]['helper_end_sec'])+.55*(candidate_metrics[s]['req_sec']-base_metrics[s]['req_sec'])for s in seeds]
  x['net_score_pct']=shared.stats(net)
  assert abs(x['net_score_pct']['mean']+x['net_improvement_pct'])<1e-10
  # The first build logged hm after an uphill escape, while its optimized cost
  # and returned design already referred to best_mask. Recover the comparable
  # raw gobj from that cost and the actual returned handle set for every run.
  av=[base_metrics[s]['gobj_after']for s in seeds]
  bv=[candidate_metrics[s]['gobj_bias_after']+candidate_metrics[s]['gbias_lambda']*candidate[s][0]for s in seeds]
  x['metrics']['gobj_after_logged']=x['metrics']['gobj_after']
  x['metrics']['gobj_after']={'n':len(seeds),'difference':shared.stats([b-a for a,b in zip(av,bv)]),'base_mean':shared.st.mean(av),'candidate_mean':shared.st.mean(bv),'base_p99':shared.p99(av),'candidate_p99':shared.p99(bv)}
  x['gobj_after_reconstructed_from_saved_design']=True
  x['design_bias']={}
  for i,key in enumerate(['B','minority_share']):
   av=[baseline[s][i]for s in seeds];bv=[candidate[s][i]for s in seeds]
   x['design_bias'][key]={'base_mean':shared.st.mean(av),'candidate_mean':shared.st.mean(bv),'difference':shared.stats([b-a for a,b in zip(av,bv)])}
name=f'gbias-{a.suite}'+(f'-{a.end}'if a.end else '')
(notes/(name+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for x in out:
 print(x['base'],'->',x['candidate'],'n',x['n'],'WA',x['wa'],'score',x['score_pct'],'W/T/L',x['wtl'])
 for key,v in x['metrics'].items():print(key,v)
 for key in ['candidate_only_metrics','design_bias','stdout_different','time_charge_pct','net_improvement_pct','net_score_pct','outside_load','extensions']:
  if key in x:print(key,x[key])
