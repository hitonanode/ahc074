#!/usr/bin/env python3
"""Exhaustive tiny-graph check of family deduplication and K-invariant ties."""
import random,json
from dataclasses import dataclass
@dataclass(frozen=True)
class Edge:
 lo:int
 hi:int
 gain:int
 family:int
 @property
 def key(self):return(self.hi,self.family)
def one_best(n,edges):
 score=[0]*(n+1);paths=[()]*(n+1)
 for c in range(n):
  score[c+1]=score[c];paths[c+1]=paths[c]
  for e in edges[c]:
   v=score[e.lo]+e.gain
   if v>score[c+1]:score[c+1]=v;paths[c+1]=paths[e.lo]+(e.key,)
 return paths[n]
def truncated(n,edges,k):
 dp=[[] for _ in range(n+1)];dp[0]=[(0,())]
 for c in range(n):
  pool=list(dp[c])
  for e in edges[c]:pool.extend((s+e.gain,p+(e.key,))for s,p in dp[e.lo])
  pool.sort(key=lambda z:-z[0]);seen=set()
  for z in pool:
   if z[1] not in seen:dp[c+1].append(z);seen.add(z[1])
   if len(dp[c+1])==k:break
 return dp[n]
def exhaustive(n,edges):
 flat=[e for row in edges for e in row];best={}
 def visit(start,score,path):
  best[path]=max(best.get(path,-10**9),score)
  for e in flat:
   if e.lo>=start:visit(e.hi+1,score+e.gain,path+(e.key,))
 visit(0,0,());return best
rng=random.Random(740115);checks=0;max_families=0
for case in range(2000):
 n=rng.randrange(1,6);edges=[]
 for c in range(n):
  row=[]
  for f in range(rng.randrange(1,4)):
   for lo in range(c+1):
    if rng.random()<.7:row.append(Edge(lo,c,rng.randrange(-2,11),f))
  edges.append(row)
 brute=exhaustive(n,edges);max_families=max(max_families,len(brute));original=one_best(n,edges)
 full=truncated(n,edges,9);reference=[p for v,p in full if p!=original]
 for rank in range(1,8):
  found=truncated(n,edges,rank+1)
  assert len({p for _,p in found})==len(found)
  assert [v for v,p in found]==sorted(brute.values(),reverse=True)[:rank+1]
  assert all(brute[p]==v for v,p in found)
  alts=[p for v,p in found if p!=original]
  if len(alts)>=rank:assert alts[rank-1]==reference[rank-1]
  checks+=1
print(json.dumps(dict(random_graphs=2000,top_k_checks=checks,max_families=max_families,all_passed=True),indent=2))
