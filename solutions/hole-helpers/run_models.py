from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'models';out.mkdir(exist_ok=True)
def job(item):
 seed,columns=item;name=f'{seed:04d}-c{columns}'
 with (out/f'{name}.err').open('w') as log:
  p=subprocess.run(['/tmp/ahc074-hole-helpers',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt',str(columns),'20000','1.8'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=300)
 r=json.loads(p.stdout);r['seed']=seed;(out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,columns,r['difference'],r['novel'],flush=True);return r
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(job,[(s,c) for s in range(24,32) for c in (6,10,14)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
