from pathlib import Path
import argparse, collections, json, re, statistics as st
p=argparse.ArgumentParser();p.add_argument('stamp');a=p.parse_args()
here=Path(__file__).parent;root=Path('/home/sato/ahc074/runs');results={}
for suffix,original in [('argon-req-budget-base-profile','argon-des-perf-latew105'),('argon-req-budget-adapt-profile','argon-req-budget-adapt')]:
 run=root/(a.stamp+'_'+suffix);ref=root/('20261106-075637_'+original)
 metrics=collections.defaultdict(list);stages=collections.defaultdict(lambda:[0,0.,0.]);groups=collections.defaultdict(lambda:[0,0.,0.,0.]);count=0
 for f in sorted(run.glob('err/*.txt'))+sorted(run.glob('orders/*/err/*.txt')):
  rel=f.relative_to(run);out=rel.parent.parent/'out'/rel.name
  assert (run/out).read_bytes()==(ref/out).read_bytes(),str(out)
  s=f.read_text();t=(ref/rel).read_text()
  norm=lambda q:[l for l in q.splitlines() if l.startswith(('@paper','@ops'))]
  assert norm(s)==norm(t)
  count+=1;times={}
  for line in s.splitlines():
   m=re.fullmatch(r'(\w+) = ([-+\d.eE]+)',line)
   if m:metrics[m[1]].append(float(m[2]))
   if line.startswith('#f3post '):
    v=line.split();stage=int(v[2]);k=(int(v[1]),int(v[3]),stage-4)
    stages[stage][0]+=1;stages[stage][1]+=float(v[7]);stages[stage][2]+=float(v[9])
    if stage>=5:times[k]=float(v[9])
   if line.startswith('#heavycand '):
    v=line.split();r,round_,rank=int(v[1]),int(v[2]),int(v[4]);gain=float(v[13]);seconds=times.get((r,round_,rank),0.)
    labels=['all','origin='+v[3],'rank='+v[4], 'repeats='+str(int(v[8])>0),
            'dead='+str(int(v[9])>0),'added='+str(int(v[11])>0),
            'hides='+str(int(v[16])>0),'raw_better='+str(float(v[7])< -1e-9),
            'repeat_dead='+str((int(v[8])>0,int(v[9])>0)),
            'repeat_origin='+str((int(v[8])>0,v[3]))]
    for label in labels:
     z=groups[label];z[0]+=1;z[1]+=gain;z[2]+=seconds;z[3]+=gain>1e-8
 result={'files':count,'metrics':{k:st.mean(v) for k,v in metrics.items()},
         'stages':{str(k):[z/count for z in v] for k,v in stages.items()},
         'groups':{k:[z/count for z in v] for k,v in groups.items()}}
 results[suffix]=result
 print(suffix,'identical stdout/paper/ops',count,flush=True)
 for k,v in result['metrics'].items():
  if k.startswith('cfprof_') and k.endswith('_exc'):print(k,v,flush=True)
 print('stages calls gain sec',result['stages'],flush=True)
 print('candidate groups: calls gain seconds improved',result['groups'],flush=True)
(here/'results.json').write_text(json.dumps(results,indent=2)+'\n')
