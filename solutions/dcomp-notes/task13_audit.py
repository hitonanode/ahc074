"""Final read-only metadata/source/result audit; flock + nice required."""
from pathlib import Path
import json,hashlib,re
N=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs');W=N.parents[1]
freeze=json.loads((N/'t13-freeze.json').read_text());x=json.loads((N/'t13-final-runs.json').read_text());out={}
assert set(x)=={'t13-final-gcc','t13-final-clang'}
for tag,ids in x.items():
 count=2000 if tag.endswith('gcc')else 500
 for rid in ids:
  d=R/rid;m=json.loads((d/'meta.json').read_text());cs=json.loads((d/'result.json').read_text())['cases']
  name=rid.split('_',1)[1];sha=hashlib.sha256((d/'src/main.cpp').read_bytes()).hexdigest()
  assert m['status']=='ok'and m['record']and len(cs)==count
  assert sorted(int(c['seed'])for c in cs)==list(range(count))and all(c['score']>0 for c in cs)
  assert sha==freeze[name]==hashlib.sha256((W/'solutions'/name/'main.cpp').read_bytes()).hexdigest()
  metrics=json.loads((d/'metrics.json').read_text())['cases'];errors=sum(q['E']for q in metrics.values());assert errors==0
  out[rid]={'status':m['status'],'record':m['record'],'count':count,'E':errors,'sha256':sha,'outside_load':m.get('outside_load'),'source_size':(d/'src/main.cpp').stat().st_size}
for tag in ['t13-final-gcc','t13-final-clang']:
 q=json.loads((N/(tag+'.json')).read_text())
 assert all(v['budget']['min']==v['budget']['max']for v in q['deadline'].values())
store=json.loads((N/'t13-store-check.json').read_text());assert all(v['same']==50 for v in store['replays'].values())
build=json.loads((N/'t13-submission-builds.json').read_text());assert build['sha256']==freeze['dcomp-time-target']
out['store']=store;out['builds']=build;out['patch']=json.loads((N/'t13-patch-audit.json').read_text())
(N/'t13-audit.json').write_text(json.dumps(out,indent=2)+'\n');print('Task13 final audit passed')
