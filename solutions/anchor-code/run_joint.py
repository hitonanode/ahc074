from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'joint';out.mkdir(exist_ok=True)
def job(item):
 seed,g=item;name=f'{seed:04d}-g{g}'
 with (out/f'{name}.err').open('w') as log:
  p=subprocess.run(['/tmp/ahc074-anchor-joint',str(root/'tools/in'/f'{seed:04d}.txt'),str(g),'0','100000','200000'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
 r=json.loads(p.stdout);r['seed']=seed;(out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,g,r.get('design_cost'),r.get('optimistic_cost'),r['eligible'],flush=True);return r
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(job,[(s,g) for s in range(24,28) for g in (36,38,40)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
