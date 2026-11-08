"""Frozen-input and per-compiler identities for Task12 screens. Run locked + nice."""
from pathlib import Path
import json,re,hashlib
N=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
def runs(tag):
 rs=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',(N/(tag+'.log')).read_text(),re.M)
 for r in rs:
  m=json.loads((R/r/'meta.json').read_text());assert m['status']=='ok'
  c=json.loads((R/r/'result.json').read_text())['cases'];assert len(c)==500 and all(x['score']>0 for x in c)
 return rs
def identity(a,b,design=False):
 same=0;different=[]
 for i in range(500):
  x=(R/a/'out'/f'{i:04d}.txt');y=(R/b/'out'/f'{i:04d}.txt')
  if design:
   def head(p):
    with p.open('rb')as f:return b''.join(f.readline()for _ in range(192))
   ok=head(x)==head(y)
  else:ok=x.read_bytes()==y.read_bytes()
  if ok:same+=1
  else:different.append(i)
 return {'reference':a,'candidate':b,'design_only':design,'same':same,'total':500,'different':different}
g=runs('t12-screen-gcc');s=runs('t12-slack');c=runs('t12-screen-clang');f=runs('t12-funded-clang')
o=[]
for r in g[1:]:o.append(identity(g[0],r,True))
for a,b in zip(g[2:],s[1:]):o.append(identity(a,b))
for r in f[1:]:o.append(identity(f[0],r,True))
o.append(identity(f[2],f[4]));o.append(identity(c[2],f[3]))
assert all(v['same']==500 for v in o),o
(N/'t12-screen-audit.json').write_text(json.dumps(o,indent=2)+'\n')
print(json.dumps(o,indent=2))
