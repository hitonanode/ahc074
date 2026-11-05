#!/usr/bin/env python3
"""DesignStore and stderr analysis only; no solution or tester execution."""
from pathlib import Path
import argparse, statistics as st
p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');p.add_argument('--seeds',type=int);args=p.parse_args()
root=Path('/home/sato/ahc074/runs')
allowed=None
if args.seeds is not None:
 allowed=set()
 for seed in range(args.seeds):
  tokens=(Path('/home/sato/ahc074/tools/in')/f'{seed:04d}.txt').read_text().split()
  h=0xcbf29ce484222325
  for word in tokens[4:260]:
   x=int(word[::-1],2)
   for byte in range(8):h=((h^((x>>(8*byte))&255))*0x100000001b3)&((1<<64)-1)
  allowed.add(f'{h:016x}.txt')
def read(f):
 d={}
 for line in f.read_text().splitlines():
  a=line.split()
  if not a:continue
  key=a[0]
  if key=='stderr':break
  if key in ['permutation','A','edge','polarity','papers','columns','ded','handle']:
   d[key]=list(map(int,a[2:]));assert len(d[key])==int(a[1])
  elif key in ['M','G','H','emergency']:d[key]=int(a[1])
 return d
for name in args.runs:
 r=root/name;rows=[]
 for f in sorted((r/'design').glob('*.txt')):
  # DesignStore names files by the FNV-1a hash of the 256 targets.
  if allowed is not None and f.name not in allowed:continue
  d=read(f)
  if d.get('emergency'):continue
  groups={}
  for u,k in enumerate(d['ded']):groups.setdefault(k,[]).append(u)
  hm=sum(1<<j for j in d['handle']);gm=(1<<d['G'])-1
  pd=[];pg=[];tri=[];shallow=[];after=[];before=[];perf=[]
  for k,us in groups.items():
   c=d['columns'][k];diff=d['A'][us[0]]^d['A'][us[-1]];opa=d['papers'][2*k]
   cm=sum(1<<j for j in d['handle'][:c+1]);pr=cm&~diff
   if len(us)==2:pd.append((diff&hm).bit_count());pg.append((diff&gm).bit_count())
   for u in us:
    tri.append(d['H']-c-1);shallow.append((diff&cm).bit_count())
    before.append((hm&~pr).bit_count());after.append((hm&~opa).bit_count());perf.append((pr&~opa).bit_count())
  rows.append(dict(G=d['G'],H=d['H'],products=len(groups),pairs=len(pd),pair_handle_diff=st.mean(pd),pair_generic_diff=st.mean(pg),triangle_holes=st.mean(tri),pair_shallow_holes=st.mean(shallow),handle_holes_before_perforation=st.mean(before),handle_holes_after_perforation=st.mean(after),perforation_holes_per_target=st.mean(perf)))
 print(name,'designs',len(rows))
 if rows:
  for key in rows[0]:print(key,st.mean(v[key] for v in rows))
