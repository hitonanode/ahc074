from pathlib import Path
import argparse, re, json
import numpy as np
p=argparse.ArgumentParser();p.add_argument('stamp');p.add_argument('--end',type=int,default=200);args=p.parse_args()
here=Path(__file__).parent;root=Path('/home/sato/ahc074/runs')
base=root/(args.stamp+'_argon-des-perf-latew105');trial=root/(args.stamp+'_argon-req-budgetparts')
data=np.empty((2*args.end,1024,7,19));metrics=[];rx=re.compile(r'^(\w+) = ([-+\d.eE]+)$',re.M)
for order in range(2):
 for seed in range(args.end):
  prefix=Path('.') if order==0 else Path('orders')/str(order)
  rel=prefix/'err'/f'{seed:04d}.txt';out=prefix/'out'/rel.name
  s=(trial/rel).read_text();t=(base/rel).read_text()
  assert (trial/out).read_bytes()==(base/out).read_bytes()
  norm=lambda q:[l for l in q.splitlines() if l.startswith(('@paper','@ops'))]
  assert norm(s)==norm(t)
  m={k:float(v) for k,v in rx.findall(s)};metrics.append(m)
  assert all(m[f'budget_{j}_invalid']==0 for j in range(7))
  assert m['budget_0_gain']==0 and m['budget_0_moves']==0
  observations=' '.join(line[8:] for line in s.splitlines() if line.startswith('#budget '))
  z=np.fromstring(observations,sep=' ').reshape(1024,7,17)
  data[order*args.end+seed,:,:,0]=seed
  data[order*args.end+seed,:,:,1]=order
  data[order*args.end+seed,:,:,2:]=z
a=data.reshape(-1,7,19);np.save(here/'observations.npy',a)
print('identical stdout/paper/ops',2*args.end,'all control values/moves identical',flush=True)
means={k:float(np.mean([m[k] for m in metrics])) for k in metrics[0] if k.startswith('budget_')}
(here/'metrics.json').write_text(json.dumps(means,indent=2)+'\n');print('means',means,flush=True)
a=a[a[:,0,2]>0]
print('without request0; time relative to replay control',flush=True)
for name,idx,bounds in [('all',4,[0,100]),('ordinary',5,[0,5,8,10,12,15,100]),
 ('holes',6,[0,3,6,9,12,15,25]),('depth',8,[0,1,2,3,4,5,100]),('fillers',9,[0,1,2,3,10]),
 ('gap',11,[-1,.01,.1,.25,.5,1,2,100]),('first_gain',12,[-100,1e-8,.02,.05,.1,.25,.5,1,100])]:
 print('\nFEATURE',name,flush=True)
 for lo,hi in zip(bounds,bounds[1:]):
  mask=(a[:,0,idx]>=lo)&(a[:,0,idx]<hi)
  for mode in range(1,7):
   gain=a[mask,mode,15];dt=a[mask,mode,17]-a[mask,0,17]
   if not len(gain):continue
   print(f'{lo:g}..{hi:g} mode{mode} n={len(gain)} gain/case={gain.sum()/(2*args.end):.5f} '
         f'dt/case={dt.sum()/(2*args.end):.6f} '
         f'gain/order={gain.mean():.6f} us/order={dt.mean()*1e6:.2f}',flush=True)
