#!/usr/bin/env python3
"""Aggregate saved logs/results; never runs a solution or tester."""
from pathlib import Path
import argparse, json, math, re, statistics as st
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('--seeds',type=int);a=p.parse_args()
root=Path('/home/sato/ahc074/runs')
def read(name):
 r=root/name;data=json.loads((r/'result.json').read_text());cases={v['seed']:v for v in data['cases']};logs={}
 for seed,v in cases.items():
  for j in range(len(v.get('order_scores',[v['score']]))):
   f=(r if j==0 else r/'orders'/str(j))/'err'/f'{seed:04d}.txt'
   if f.exists():logs[seed,j]={k:float(x) for k,x in re.findall(r'^([\w]+) = ([-+\d.eE]+)$',f.read_text(),re.M)}
 return r,cases,logs
ra,ca,la=read(a.base);rb,cb,lb=read(a.candidate)
seeds=sorted(s for s in ca.keys()&cb.keys() if a.seeds is None or s<a.seeds);ds=[];wa=[0,0]
for s in seeds:
 aa=ca[s].get('order_scores',[ca[s]['score']]);bb=cb[s].get('order_scores',[cb[s]['score']]);wa[0]+=sum(x<=0 for x in aa);wa[1]+=sum(x<=0 for x in bb)
 xx=[100*math.log(y/x) for x,y in zip(aa,bb) if x>0 and y>0]
 if xx:ds.append(st.mean(xx))
print(a.base,a.candidate,'seeds',len(seeds),'orders',len(ca[seeds[0]].get('order_scores',[0])),'WA',wa)
print('log %',st.mean(ds),'SE',st.stdev(ds)/math.sqrt(len(ds)) if len(ds)>1 else 0,'W/T/L',sum(x<-1e-12 for x in ds),sum(abs(x)<=1e-12 for x in ds),sum(x>1e-12 for x in ds))
keys=sorted(k for k in la.keys()&lb.keys() if k[0] in seeds)
metrics=['gobj_before','gobj_after','map_end_sec','anneal_end_sec','climb_end_sec','match_end_sec','perforation_end_sec','helper_end_sec','req_sec','end_sec','model_cost','proxy_after','generic_moves','total_moves','self_wrong','op_label_errors']
metrics+=sorted(k for k in lb[keys[0]] if k.startswith(('qm_','model_','cost_','handle_','pair_')) and k not in metrics)
for name in metrics:
 xs=[la[k][name] for k in keys if name in la[k]];ys=[lb[k][name] for k in keys if name in lb[k]]
 if not ys:continue
 if not xs: print(name,'candidate',st.mean(ys));continue
 x,y=st.mean(xs),st.mean(ys)
 print(name,f'{x:.9f} -> {y:.9f}','ratio',y/x if x else None)
for name,logs in [(a.base,la),(a.candidate,lb)]:
 ts=sorted(logs[k]['end_sec'] for k in keys);print(name,'end>1.8/1.9/2.0',*[sum(t>c for t in ts) for c in [1.8,1.9,2]],'p99',ts[int(.99*(len(ts)-1))],'max',max(ts))
