"""Train only on probe seeds 0..99; check fixed ranking on 100..199.
Run after the completed probe, under the shared lock. No solver is run here.
"""
from pathlib import Path
import json,sys,numpy as np
P=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs');run=sys.argv[1]
assert json.loads((R/run/'meta.json').read_text())['status']=='ok'
cases=json.loads((R/run/'result.json').read_text())['cases']
assert len(cases)==200 and all(int(c['seed'])<200 and len(c['order_scores'])==2 and min(c['order_scores'])>0 for c in cases)
# one array per (seed, list, request, round), preserving the existing rank
rows=[];groups=[];current=None;group=[]
ops={'eject':0,'22':1,'11':2,'32':3,'plans':4}
for order in range(2):
 ep=R/run/('err' if order==0 else f'orders/{order}/err')
 for file in sorted(ep.glob('*.txt')):
  seed=int(file.stem)
  for line in file.read_text().splitlines():
   if not line.startswith('#heavycand '):continue
   a=line.split();key=(seed,order,int(a[1]),int(a[2]))
   if key!=current:
    if group:groups.append((current,group))
    current=key;group=[]
   # length delta, value delta, repeated moves, hidden old owner, origin, actual gain
   group.append([int(a[6])-int(a[5]),float(a[7]),int(a[8]),int(a[16]),ops[a[3]],max(0.,float(a[14]))])
if group:groups.append((current,group))
G=len(groups);width=max(len(x[1]) for x in groups)
x=np.zeros((G,width,6));valid=np.zeros((G,width),bool);seed=np.empty(G,int)
for i,(key,g) in enumerate(groups):
 x[i,:len(g)]=g;valid[i,:len(g)]=True;seed[i]=key[0]
y=x[:,:,5];oracle=y.max(axis=1);base=y[:,:3].max(axis=1)
train=seed<100;test=~train
# Smaller score is preferred. Controls include exact existing order and raw value.
def evaluate(score):
 score=np.where(valid,score,np.inf)
 idx=np.argsort(score,axis=1,kind='stable')[:,:3]
 return np.take_along_axis(y,idx,axis=1).max(axis=1)
results=[]
for vl in [0,.25,.5,1,2]:
 for hl in [0,.125,.25,.5,1,2]:
  for rl in [0,.125,.25,.5,1]:
   score=x[:,:,0]+vl*x[:,:,1]-hl*x[:,:,3]-rl*x[:,:,2]
   got=evaluate(score);results.append((got[train].mean(),vl,hl,rl,got[test].mean(),(got-base)[test].mean()))
results.sort(reverse=True)
out={'run':run,'groups':G,'width':width,'seed_split':[100,200],
 'baseline':[float(base[train].mean()),float(base[test].mean())],
 'oracle':[float(oracle[train].mean()),float(oracle[test].mean())],
 'top_train':results[:20]}
(P/'rank_fit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
np.savez_compressed(P/'rank_probe.npz',x=x,valid=valid,seed=seed)
