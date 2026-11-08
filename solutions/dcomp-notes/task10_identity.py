"""Check all stdout streams, and optionally the first 192 design lines."""
from pathlib import Path
import argparse,json
p=argparse.ArgumentParser();p.add_argument('a');p.add_argument('b');p.add_argument('--orders',type=int,default=1);p.add_argument('--seeds',default='0-500');p.add_argument('--design',action='store_true');p.add_argument('--output',required=True);args=p.parse_args()
root=Path('/home/sato/ahc074/runs');lo,hi=map(int,args.seeds.split('-'))
for d in (root/args.a,root/args.b):assert json.loads((d/'meta.json').read_text())['status']=='ok'
errors=[];n=0
for j in range(args.orders):
    rel=Path('out') if j==0 else Path('orders')/str(j)/'out'
    for seed in range(lo,hi):
        paths=[root/a/rel/f'{seed:04d}.txt' for a in (args.a,args.b)]
        if not paths[0].exists():paths=[root/a/rel/f'{seed}.txt' for a in (args.a,args.b)]
        a,b=[p.read_bytes() for p in paths]
        if args.design:a,b=[s.splitlines()[:192] for s in (a,b)]
        n+=1
        if a!=b:errors.append([seed,j])
result={'a':args.a,'b':args.b,'design_only':args.design,'n':n,'same':n-len(errors),'different':errors}
Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({**result,'different':errors[:20]}))
