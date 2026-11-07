"""Property test: compressed top-two display equals full arbitrary edit replay."""
import random
r=random.Random(730451);K=192;ALL=(1<<64)-1
def apply(order,edits):
 o=order[:]
 for k,a in edits:
  o.remove(k);o.insert(0 if a<0 else o.index(a)+1,k)
 return o
def layers(o,papers):
 seen=twice=shown=second=0;owned={}
 for k in o:
  cover,color=papers[k];one=cover&~seen;two=cover&seen&~twice
  if one:owned[k]=one
  shown|=color&one;second|=color&two;seen|=cover;twice|=two
 return seen,twice,shown,second,owned
for trial in range(2000):
 papers=[(r.getrandbits(64),r.getrandbits(64)) for _ in range(K)]
 papers=[(a,b&a) for a,b in papers]
 initial=list(range(K));r.shuffle(initial)
 edits=[]
 for _ in range(r.randrange(2,25)):
  k=r.randrange(K);a=r.randrange(-1,K-1);a+=a>=k;edits.append((k,a))
 moving={k for k,a in edits};essential=moving|{a for k,a in edits if a>=0}
 once=twice=0
 for k in initial:
  if k in moving:continue
  cover=papers[k][0]
  if cover&~twice:essential.add(k)
  twice|=once&cover;once|=cover
 skeleton=[k for k in initial if k in essential]
 drop=set(r.sample(range(len(edits)),min(2,len(edits))))
 path=[e for i,e in enumerate(edits) if i not in drop]
 full=apply(initial,path);small=apply(skeleton,path)
 assert small==[k for k in full if k in essential]
 assert layers(full,papers)==layers(small,papers)
print('PASS 2000 arbitrary stacks, masks, repeated edits and two deletions')
