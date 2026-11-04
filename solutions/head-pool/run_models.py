from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'models';out.mkdir(exist_ok=True)
def job(item):
    seed,samples=item;name=f'{seed:04d}-s{samples}'
    with (out/f'{name}.err').open('w')as log:
        p=subprocess.run(['/tmp/ahc074-head-pool',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt','16',str(samples),'2'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
    r=json.loads(p.stdout)
    for v in r:v.update(seed=seed)
    (out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,samples,r[1]['difference'],r[1]['changed'],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=sum(pool.map(job,[(s,n)for s in range(24,40)for n in (4,16)]),[])
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for n in (4,16):
    v=[r['difference']for r in rows if r['mode']==1 and r['samples']==n];print(n,statistics.mean(v),statistics.stdev(v)/math.sqrt(len(v)),flush=True)
