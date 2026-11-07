from pathlib import Path
import json,re,math,sys
P=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
def mean(v):return sum(v)/len(v)
def se(v):m=mean(v);return math.sqrt(sum((x-m)**2 for x in v)/(len(v)-1)/len(v))
def ready(r):
 try:return json.loads((R/r/'meta.json').read_text()).get('status')=='ok' and (R/r/'result.json').exists() and (R/r/'metrics.json').exists()
 except (OSError,ValueError):return False
def load(r):
 x=json.loads((R/r/'result.json').read_text());c={int(z['seed']):z for z in x['cases']};m=json.loads((R/r/'metrics.json').read_text())['cases'];return c,{int(k):z['stderr'] for k,z in m.items()}
def jud(x):return 1.04*x['helper_end_sec']+1.35*x['req_sec']+x['end_sec']-x['helper_end_sec']-x['req_sec']
def q(v,p):v=sorted(v);a=p*(len(v)-1);i=int(a);return v[i]+(a-i)*(v[min(i+1,len(v)-1)]-v[i])
outputs=[]
for name in ['map-speed','req-speed','perf-copy','key-speed','eject-simd','filler-pack','map-bits','vdp-speed','map-cyclic','map-defer','map-gather-clang','vcap-speed']:
 f=P/(name+'.log')
 if not f.exists():continue
 ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',f.read_text(),re.M)
 if not ids or not all(ready(x) for x in ids):continue
 a,am=load(ids[0]);seeds=sorted(a)
 for run in ids[1:]:
  b,bm=load(run);assert sorted(b)==seeds and all(b[i]['score']>0 for i in seeds)
  same=sum((R/ids[0]/'out'/f'{i:04d}.txt').read_bytes()==(R/run/'out'/f'{i:04d}.txt').read_bytes() for i in seeds)
  row={'kind':'speed','ref':ids[0],'run':run,'n':len(seeds),'identical':same}
  for key in ['map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','helper_end_sec','req_sec','end_sec']:
   v=[bm[i][key]-am[i][key] for i in seeds];row[key]=[mean(v),se(v)]
  v=[jud(bm[i])-jud(am[i]) for i in seeds];row['judge_delta']=[mean(v),se(v)];row['judge_ratio']=mean([jud(bm[i]) for i in seeds])/mean([jud(am[i]) for i in seeds]);row['outside_load']=json.loads((R/run/'meta.json').read_text()).get('outside_load');outputs.append(row)
ref='20261107-113720_deval-seven-wide';a,am=load(ref)
if (P/'experiments.jsonl').exists():
 for line in (P/'experiments.jsonl').read_text().splitlines():
  row=json.loads(line);run=row['replay'];b,bm=load(run);seeds=sorted(b);assert seeds==list(range(500))
  z={'kind':'quality','run':run,'tag':row['tag'],'design':row['design']}
  for key,sl in [('fresh',slice(1,8)),('all',slice(0,8)),('real',slice(0,1))]:
   v=[100*math.log(mean(b[i]['order_scores'][sl])/mean(a[i]['order_scores'][sl])) for i in seeds];z[key]=[mean(v),se(v)]
  _,m=load(row['design']);_,m0=load(row['normal_references'][1]);_,old=load(row['normal_references'][0]);_,nofb=load(row['normal_references'][2]);
  z['judge_ratio_old']=mean([jud(m[i]) for i in seeds])/mean([jud(old[i]) for i in seeds]);z['judge_p99']=[q([jud(m[i]) for i in seeds],.99),q([jud(nofb[i]) for i in seeds],.99)]
  z['design_delta']=[mean([m[i]['helper_end_sec']-m0[i]['helper_end_sec'] for i in seeds]),se([m[i]['helper_end_sec']-m0[i]['helper_end_sec'] for i in seeds])]
  z['outside_load']=json.loads((R/row['design']/'meta.json').read_text()).get('outside_load')
  outputs.append(z)
for name in ['req-search','req-value','terminal']:
 f=P/(name+'.log')
 if not f.exists():continue
 ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',f.read_text(),re.M)
 if not ids or not all(ready(x) for x in ids):continue
 a,am=load(ids[0]);seeds=sorted(a)
 for run in ids[1:]:
  b,bm=load(run);assert sorted(b)==seeds
  z={'kind':'request','ref':ids[0],'run':run,'n':len(seeds)}
  for key,sl in [('all4',slice(0,4)),('fresh3',slice(1,4)),('real',slice(0,1))]:
   v=[100*math.log(mean(b[i]['order_scores'][sl])/mean(a[i]['order_scores'][sl])) for i in seeds];z[key]=[mean(v),se(v)]
  v=[bm[i]['req_sec']-am[i]['req_sec'] for i in seeds];z['req_delta']=[mean(v),se(v)];outputs.append(z)
(P/'summary.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2)+'\n')
for x in outputs:print(json.dumps(x,ensure_ascii=False))
