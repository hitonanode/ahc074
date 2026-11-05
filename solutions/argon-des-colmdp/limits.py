"""Inspect saved designs only, no future orders. Run via whenidle + exclusive runs/.lock."""
from pathlib import Path
import json,math,itertools,functools,collections
here=Path(__file__).resolve().parent
root=here.parents[1];runs=Path('/home/sato/ahc074/runs')
name='20261106-062412_argon-des-perf-latew105'
def read_design(path):
 result={}
 vectors={'permutation','A','edge','polarity','papers','columns','ded','handle'}
 for line in path.read_text().splitlines():
  key,*v=line.split()
  if key=='stderr':break
  if key in vectors:result[key]=list(map(int,v[1:]))
  elif key in {'M','G','H','emergency'}:result[key]=int(v[0])
 return result
@functools.cache
def states(cnt):
 full=math.factorial(sum(cnt))//math.prod(math.factorial(c)for c in cnt)
 total=sum(math.factorial(sum(v))//math.prod(math.factorial(x)for x in v)for v in itertools.product(*(range(c+1)for c in cnt)))
 return full,total
rows=[];binding=collections.Counter();lengths=collections.Counter();covered=collections.Counter()
for seed in range(2000):
 with (root/'tools/in'/f'{seed:04d}.txt').open()as f:
  header=list(map(int,f.readline().split()));assert header[2]==256
  h=0xcbf29ce484222325
  for _ in range(256):
   s=f.readline().strip();x=sum((v=='1')<<i for i,v in enumerate(s))
   for byte in range(8):h=((h^((x>>(8*byte))&255))*0x100000001b3)&((1<<64)-1)
 d=read_design(runs/name/'design'/f'{h:016x}.txt')
 freq=collections.Counter(d['ded']);counts=[[0]*4 for _ in range(d['H'])]
 for k,c in enumerate(d['columns']):
  if c>=0:counts[c][2*(freq[k]>=2)+((d['papers'][2*k+1]>>d['handle'][c])&1)]+=1
 bad=[]
 for c,cnt in enumerate(counts):
  n=sum(cnt);full,total=states(tuple(cnt));lengths[n]+=1
  reasons=[r for r,fail in [('length',n>14),('full',full>40000),('sequences',total>250000)]if fail]
  if reasons:
   binding['+'.join(reasons)]+=1
   bad.append(dict(column=c,count=cnt,length=n,full=full,sequences=total,reasons=reasons))
 covered[d['H']-len(bad)]+=1
 if bad:rows.append(dict(seed=seed,columns=bad))
result=dict(run=name,n=2000,affected=len(rows),binding=dict(binding),lengths=dict(lengths),covered=dict(covered),rows=rows)
(here/'limits.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k!='rows'},indent=2))
