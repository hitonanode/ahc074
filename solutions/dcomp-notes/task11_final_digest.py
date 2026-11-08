"""Small human-readable digest of the completed final analysis; no refitting."""
from pathlib import Path
import json
N=Path(__file__).resolve().parent
p=N/'t11-final-normal.json'
if p.exists():
 d=json.loads(p.read_text());alt,cand=d['runs'][2:]
 for ref,r in d['comparisons'][cand].items():
  for group,z in r.items():
   print('normal',cand,'vs',ref,group,z['pct']['mean'],z['pct']['se'],z['wtl'])
 for r,t in d['timing'].items():
  print('time',r,'judge',t['judge_sec'],'ratio',t['judge_ratio_argon'],'end',t['end_sec'],'above',t['end_above'])
 print('paired',d['paired']);print('p99',d['p99']);print('design_identity',d['design_identity']);print('outside',d['outside_load'])
p=N/'t11-final-replay.json'
if p.exists():
 d=json.loads(p.read_text())
 for group,v in d['groups'].items():
  for orders,z in v.items():print('replay',group,orders,z)
p=N/'t11-final-clang.json'
if p.exists():
 d=json.loads(p.read_text());print('clang reference',d['reference'])
 for r,v in d['results'].items():
  print('clang',r,'score',v['score_pct'])
  for k in ['helper_end_sec','req_sec','end_sec','judge_sec']:
   print(k,v['metrics'].get(k))
