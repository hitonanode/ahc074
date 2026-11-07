"""Attribute total move differences to order ranges, without invoking the solver."""
from pathlib import Path
import json,math,sys
R=Path('/home/sato/ahc074/runs')
def costs(p):
 with p.open() as f:
  for _ in range(192):next(f)
  out=[]
  for _ in range(1024):
   n=int(next(f));out.append(n)
   for _ in range(n):next(f)
  return out
ref=sys.argv[1];outputs=[]
for run in sys.argv[2:]:
 meta=json.loads((R/run/'meta.json').read_text());assert meta['status']=='ok'
 rows=[]
 for seed in range(500):
  a=costs(R/ref/'out'/f'{seed:04d}.txt');b=costs(R/run/'out'/f'{seed:04d}.txt');rows.append([y-x for x,y in zip(a,b)])
 z={'reference':ref,'candidate':run,'groups':[]}
 for lo,hi in [(0,1),(0,16),(16,64),(64,256),(256,1024),(0,1024)]:
  a=[sum(x[lo:hi]) for x in rows];m=sum(a)/len(a);se=(sum((x-m)**2 for x in a)/(len(a)-1)/len(a))**.5
  z['groups'].append({'orders':[lo,hi],'move_delta':[m,se]})
 outputs.append(z);print(json.dumps(z))
Path(__file__).with_name('initial-prefix.json').write_text(json.dumps(outputs,indent=2)+'\n')
