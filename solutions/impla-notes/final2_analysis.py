"""Read recorded runs only. Run under the evaluation lock with nice."""
import argparse,hashlib,json,math,re,statistics as st
from pathlib import Path
NOTES=Path(__file__).resolve().parent
RUNS=Path('/home/sato/ahc074/runs')
RX=re.compile(r'^([A-Za-z][A-Za-z0-9_]*) = ([-+0-9.eE]+)$',re.M)

def stats(v):
 v=list(v);a=sorted(v);x=(len(a)-1)*.99;i=int(x)
 return {'n':len(v),'mean':st.mean(v),'se':st.stdev(v)/math.sqrt(len(v)) if len(v)>1 else 0.,'p99':a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i),'max':max(v)}

def runids(suite):
 spec=json.loads((NOTES/f'final2-{suite}-spec.json').read_text())
 ids=re.findall(r'\[pahcer_run\] run-id: (\S+)',(NOTES/f'final2-{suite}.log').read_text())
 assert len(ids)==len(spec['arms']),(suite,ids)
 return ids

def load(rid):
 d=RUNS/rid;meta=json.loads((d/'meta.json').read_text());cases=json.loads((d/'result.json').read_text())['cases']
 rows={};traps=[]
 for c in cases:
  seed=int(c['seed']);t=(d/'err'/f'{seed:04d}.txt').read_text();rows[seed]={k:float(v)for k,v in RX.findall(t)}
  if re.search(r'assertion .*failed|Assertion|AddressSanitizer|UndefinedBehaviorSanitizer|SIGABRT|runtime error:|terminate called',t):traps.append(seed)
 out={'run':rid,'n':len(cases),'wa':sum(c['score']<=0 for c in cases),'traps':traps,'errors':[c for c in cases if c['score']<=0],
      'source_sha256':hashlib.sha256((d/'src/main.cpp').read_bytes()).hexdigest(),'compile_command':meta['compile_command'],'outside_load':meta.get('outside_load')}
 for key in ['helper_end_sec','req_sec','end_sec']:
  values=[r[key]for r in rows.values()if key in r]
  if values:
   out[key]=stats(values)
   if key=='end_sec':out[key]['over']={str(v):sum(x>v for x in values)for v in [1.8,1.9,1.92,2.0]}
 for key in ['design_time_enabled','pace_effort0','pace_effort1','pace_effort2','pace_effort3','pace_effort4','pace_light']:
  v=[r[key]for r in rows.values()if key in r]
  if v:out[key]=stats(v)
 return out,{int(c['seed']):c for c in cases},rows

def paired(a,b):
 sa,ca,ra=load(a);sb,cb,rb=load(b);seeds=sorted(ca.keys()&cb.keys());good=[s for s in seeds if ca[s]['score']>0 and cb[s]['score']>0]
 v=[100*math.log(cb[s]['score']/ca[s]['score'])for s in good]
 out={'base':a,'candidate':b,'n':len(good),'score_pct':stats(v),'wtl':[sum(x<0 for x in v),sum(x==0 for x in v),sum(x>0 for x in v)],'times':{}}
 for key in ['helper_end_sec','req_sec','end_sec']:out['times'][key]=stats((rb[s][key]-ra[s][key])*1000 for s in good)
 return out

def identity(a,b):
 _,ca,_=load(a);_,cb,_=load(b);seeds=sorted(ca.keys()&cb.keys());different=[]
 for seed in seeds:
  if (RUNS/a/'out'/f'{seed:04d}.txt').read_bytes()!=(RUNS/b/'out'/f'{seed:04d}.txt').read_bytes():different.append(seed)
 return {'base':a,'candidate':b,'n':len(seeds),'same':len(seeds)-len(different),'different':different}

def analyze(suite):
 ids=runids(suite);out={'suite':suite,'runs':[load(r)[0]for r in ids]}
 if suite=='identity':
  out['identity']=[identity(ids[a],ids[b])for a,b in [(1,2),(4,5),(6,7)]]
  source=(NOTES.parents[1]/'solutions/final2-reset6/main.cpp').read_text()
  block=re.search(r'static constexpr Boundary boundaries\[\] = \{(.*?)\n    \};',source,re.S).group(1)
  seq=re.findall(r'\{"([^"]+)",',block)
  loaded=[load(ids[i])[2]for i in [0,2,3,5]]
  phases=[];total=0
  for name in seq:
   key='dt_'+name+'_sec';vectors=[[rows[s][key]for s in sorted(rows)]for rows in loaded]
   means=[st.mean(v)for v in vectors];old=(means[0]+means[2])/2;new=(means[1]+means[3])/2
   delta=[((b-a)+(d-c))/2 for a,b,c,d in zip(*vectors)]
   phases.append({'name':name,'base_mean_sec':old,'candidate_mean_sec':new,'relative_pct':100*(new/old-1),'paired_sec':stats(delta),'gcc':{'base':stats(vectors[0]),'candidate':stats(vectors[1])},'clang':{'base':stats(vectors[2]),'candidate':stats(vectors[3])}});total+=new
  cumulative=0
  for phase in phases:
   cumulative+=phase['candidate_mean_sec'];phase['share']=phase['candidate_mean_sec']/total;phase['cumulative']=cumulative/total
  phases[-1]['cumulative']=1.
  out['phases']=phases;out['phase_total_sec']=total
  out['phases_over_3pct']=[p['name']for p in phases if abs(p['relative_pct'])>3]
 elif suite=='identity_final':
  initial=runids('identity');out['identity']=[identity(initial[a],ids[b])for a,b in [(1,0),(4,1),(6,2)]]
 elif suite=='pattern':
  if (NOTES/'final2-identity_final-spec.json').exists():ref=runids('identity_final')[1]
  else:ref=runids('identity')[5]
  out['identity']=[identity(ref,ids[0])]
 elif suite=='normal':out['comparison']=paired(ids[0],ids[1])
 (NOTES/f'final2-{suite}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 for r in out['runs']:print(r['run'],'n',r['n'],'WA',r['wa'],'traps',r['traps'],'end',r.get('end_sec'),'load',r['outside_load'])
 for k in ['identity','comparison','phases_over_3pct']:
  if k in out:print(k,out[k])
 if 'phases' in out:
  for p in out['phases']:
   if abs(p['relative_pct'])>3:print('phase',p['name'],p['relative_pct'],'base ms',p['base_mean_sec']*1000,'candidate ms',p['candidate_mean_sec']*1000,'delta ms ±SE',p['paired_sec']['mean']*1000,p['paired_sec']['se']*1000)
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('suite');args=p.parse_args();analyze(args.suite)
