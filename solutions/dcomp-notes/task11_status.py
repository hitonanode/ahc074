"""Small read-only status/score digest from finished result.json files; no solver execution."""
from pathlib import Path
import json,re,math,statistics
N=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
for tag in __import__('sys').argv[1:]:
 p=N/f't11-{tag}.log'
 if not p.exists():continue
 ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',p.read_text(),re.M)
 if not ids:continue
 statuses=[json.loads((R/rid/'meta.json').read_text()).get('status')for rid in ids]
 print(tag,dict(zip(ids,statuses)))
 if any(st!='ok'for st in statuses):continue
 runs=[json.loads((R/rid/'result.json').read_text())for rid in ids]
 def scores(d):
  rows=d['cases'];return {int(r['seed']):r.get('order_scores',[r['score']])for r in rows}
 data=[scores(d)for d in runs];base=data[0]
 for rid,d in zip(ids[1:],data[1:]):
  z=[]
  for seed in sorted(base.keys()&d.keys()):
   if seed>=500:continue
   if not all(x>0 for x in base[seed]+d[seed]):raise ValueError('WA '+rid+str(seed))
   assert len(base[seed])==len(d[seed])
   z.append(100*statistics.mean(math.log(b/a)for a,b in zip(base[seed],d[seed])))
  print(rid,len(z),f'{statistics.mean(z):+.6f} +/- {statistics.stdev(z)/math.sqrt(len(z)):.6f}%')
