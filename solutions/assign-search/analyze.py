#!/usr/bin/env python3
"""Read recorded results only; never executes a solution or tester."""
from pathlib import Path
import argparse, json, math, re, statistics as st
p=argparse.ArgumentParser(); p.add_argument('base'); p.add_argument('candidate'); p.add_argument('--seeds',type=int); a=p.parse_args()
root=Path('/home/sato/ahc074/runs')
def read(name):
 r=root/name
 logs={int(f.stem):{k:float(v) for k,v in re.findall(r'^([\w]+) = ([-+\d.eE]+)$',f.read_text(),re.M)} for f in (r/'err').glob('*.txt')}
 result=json.loads((r/'result.json').read_text())
 return r,logs,{x['seed']:x['score'] for x in result['cases']}
ra,la,sa=read(a.base);rb,lb,sb=read(a.candidate)
ks=sorted(k for k in sa.keys()&sb.keys() if a.seeds is None or k<a.seeds); valid=[s for s in ks if sa[s]>0 and sb[s]>0]
print(a.base,a.candidate,'seeds',len(ks),'WA',sum(sa[s]==0 for s in ks),sum(sb[s]==0 for s in ks))
x=[100*math.log(sb[s]/sa[s]) for s in valid]
print('score log %',st.mean(x),'SE',st.stdev(x)/math.sqrt(len(x)) if len(x)>1 else 0,'W/T/L',sum(sb[s]<sa[s] for s in valid),sum(sb[s]==sa[s] for s in valid),sum(sb[s]>sa[s] for s in valid))
for k in ['gobj_before','gobj_after','map_end_sec','req_sec','end_sec','map_iters','gopt_steps','search_exact_evals','search_accept','window_rows','window_samples','rank_rows','rank_pairs','rank_choices','rank_positive','self_wrong','op_label_errors']:
 xs=[la[s][k] for s in ks if k in la[s]];ys=[lb[s][k] for s in ks if k in lb[s]]
 if not ys:continue
 if not xs:print(k,'candidate',st.mean(ys));continue
 x,y=st.mean(xs),st.mean(ys)
 ds=[lb[s][k]-la[s][k] for s in ks if k in lb[s] and k in la[s]]
 print(k,f'{x:.9f} -> {y:.9f}', 'ratio',y/x if x else None,'delta',st.mean(ds),'SE',st.stdev(ds)/math.sqrt(len(ds)) if len(ds)>1 else 0)
for n,logs in [(a.base,la),(a.candidate,lb)]:
 t=[logs[s]['end_sec'] for s in ks]
 print(n,'end>1.8/1.9/2.0',*[sum(v>c for v in t) for c in [1.8,1.9,2]],'max',max(t),'p99',sorted(t)[int(.99*(len(t)-1))])
print('stdout differences',sum((ra/'out'/f'{s:04d}.txt').read_bytes()!=(rb/'out'/f'{s:04d}.txt').read_bytes() for s in ks))
