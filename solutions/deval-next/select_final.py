"""Apply the predeclared runtime rule, without reading final quality scores."""
from pathlib import Path
import json,re,hashlib
P=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs');root=P.parents[1]
f=json.loads((P/'freeze.json').read_text());ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',(P/'final-normal.log').read_text(),re.M);assert len(ids)==5
stats={}
for run in ids:
 p=R/run;meta=json.loads((p/'meta.json').read_text());assert meta['status']=='ok'
 load=meta['outside_load'];assert load['mean_cores']<=.5 and load['max_cores']<=3,('outside load',load)
 a=json.loads((p/'metrics.json').read_text())['cases'];assert sorted(map(int,a))==list(range(2000));v=[]
 for c in a.values():
  d=c['stderr'];v.append(1.04*d['helper_end_sec']+1.35*d['req_sec']+d['end_sec']-d['helper_end_sec']-d['req_sec'])
 v.sort();q=.99*(len(v)-1);i=int(q);stats[run]={'mean':sum(v)/len(v),'p99':v[i]+(q-i)*(v[i+1]-v[i]),'max':v[-1]}
old=ids[0];nofb=next(r for r in ids if r.endswith('_deval-vbranch-nofb'));choice=None
for c in f['candidates']:
 run=next(r for r in ids if r.endswith('_'+c['name']));assert hashlib.sha256((R/run/'src/main.cpp').read_bytes()).hexdigest()==c['source_sha256'];assert (root/'solutions'/c['name']/'main.cpp').read_bytes()==(R/run/'src/main.cpp').read_bytes()
 stats[run]['ratio']=stats[run]['mean']/stats[old]['mean'];stats[run]['qualifies']=stats[run]['ratio']<=1.10 and stats[run]['p99']<=stats[nofb]['p99']
 if choice is None and stats[run]['qualifies']:choice={'name':c['name'],'normal_run':run}
out={'freeze_time':f['frozen_at'],'normal_runs':ids,'selection_rule':f['selection_rule'],'timing':stats,'choice':choice}
(P/'final-selection.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));assert choice,'No frozen candidate satisfies the runtime constraints'
(root/'solutions'/choice['name']/'final-selection.json').write_text(json.dumps(out,indent=2)+'\n')
