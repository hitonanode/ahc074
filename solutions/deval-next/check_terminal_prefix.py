"""Verify finite-horizon variants change only the specified final orders."""
from pathlib import Path
import json,re
R=Path('/home/sato/ahc074/runs');P=Path(__file__).resolve().parent
ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',(P/'terminal.log').read_text(),re.M)
assert len(ids)==4
for rid in ids:assert json.loads((R/rid/'meta.json').read_text())['status']=='ok'
def parse(f):
 a=f.read_bytes().splitlines(keepends=True);rows=[b''.join(a[:192])];p=192;counts=[]
 for _ in range(1024):
  n=int(a[p]);counts.append(n);rows.append(b''.join(a[p:p+n+1]));p+=n+1
 assert p==len(a)
 return rows,counts
out=[]
for rid,h in zip(ids[1:],[1,4,16]):
 same=0;ds=[]
 for i in range(500):
  a,ac=parse(R/ids[0]/'out'/f'{i:04d}.txt');b,bc=parse(R/rid/'out'/f'{i:04d}.txt');same+=a[:1025-h]==b[:1025-h]
  ds.append(sum(bc)-sum(ac))
 out.append({'reference':ids[0],'candidate':rid,'horizon':h,'unchanged_prefix':same,'cases':500,'real_mean_saved_moves':-sum(ds)/500})
 assert same==500
(P/'terminal-prefix.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
