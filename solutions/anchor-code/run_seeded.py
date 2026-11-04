from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'seeded';out.mkdir(exist_ok=True)
def job(item):
 q,g=item;name=f'0024-q{q}-g{g}'
 with (out/f'{name}.err').open('w') as log:
  p=subprocess.run(['/tmp/ahc074-anchor-seeded',str(root/'tools/in/0024.txt'),str(q),str(g),'0','500000','/home/sato/ahc074/runs/20261103-033246_as6-canon/out/0024.txt'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=900)
 r=json.loads(p.stdout);r.update(seed=24,Q=q,G=g);(out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(q,g,r.get('design_cost'),r.get('optimistic_cost'),r.get('proxy'),flush=True);return r
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(job,[(q,g) for q in (0,1,2,3,4) for g in (38,)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
