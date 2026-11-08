"""Read-only final source/result/DesignStore audit; run with flock and nice."""
from pathlib import Path
import json,hashlib
N=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
x=json.loads((N/'t12-final-runs.json').read_text());out={'runs':{},'replay_order0_identity':{},'replay_errors':{},'clang_design_identity':{}}
for kind in ['normal','replay','clang']:
 for rid in x[kind]:
  d=R/rid;m=json.loads((d/'meta.json').read_text());r=json.loads((d/'result.json').read_text())
  v={'status':m['status'],'cases':len(r['cases']),'positive':sum(c['score']>0 for c in r['cases']),
     'sha256':hashlib.sha256((d/'src/main.cpp').read_bytes()).hexdigest(),'outside_load':m.get('outside_load'),
     'source_size':(d/'src/main.cpp').stat().st_size,'record':m['record'],
     'compile_command':m['compile_command']}
  assert v['status']=='ok' and v['positive']==v['cases']
  assert v['cases']==(500 if kind=='clang' else 2000)
  assert sorted(int(c['seed']) for c in r['cases'])==list(range(v['cases']))
  assert v['sha256']==x['freeze']['hashes'][rid.split('_',1)[1]]
  assert v['record']==(kind!='replay')
  metrics=json.loads((d/'metrics.json').read_text())['cases']
  v['order0_errors']=sum(c['E'] for c in metrics.values());assert v['order0_errors']==0
  out['runs'][rid]=v
for normal,replay in zip(x['normal'][1:],x['replay']):
 same=0;different=[]
 for seed in range(2000):
  a=(R/normal/'out'/f'{seed:04d}.txt').read_bytes();b=(R/replay/'out'/f'{seed:04d}.txt').read_bytes()
  if a==b:same+=1
  else:different.append(seed)
 out['replay_order0_identity'][normal]={'same':same,'total':2000,'different':different}
 assert same==2000
for rid in x['replay']:
 d=R/rid;r=json.loads((d/'result.json').read_text());errors=[0]*4
 for case in r['cases']:
  seed=int(case['seed']);assert len(case['order_scores'])==4
  for j,score in enumerate(case['order_scores']):
   p=(d if j==0 else d/'orders'/str(j))/'out'/f'{seed:04d}.txt'
   lines=p.read_bytes().splitlines();assert len(lines)>=192+1024
   counts=[int(line) for line in lines[192:] if b' ' not in line]
   assert len(counts)==1024 and sum(counts)+1024+192==len(lines)
   penalty=score-sum(counts);assert penalty>=0 and penalty%384==0
   errors[j]+=penalty//384
 assert errors==[0]*4
 out['replay_errors'][rid]={'cases':2000,'order_lists':4,'E_per_list':errors}
base,dual,candidate=x['clang'];same=0
for seed in range(500):
 def papers(rid):
  with (R/rid/'out'/f'{seed:04d}.txt').open('rb') as f:
   return b''.join(f.readline() for _ in range(192))
 same+=papers(base)==papers(candidate)
assert same==500
out['clang_design_identity']={'same':same,'total':500}
(N/'t12-final-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
