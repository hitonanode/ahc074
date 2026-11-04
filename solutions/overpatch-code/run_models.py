from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'models';out.mkdir(exist_ok=True)
def job(item):
    seed,charge=item;name=f'{seed:04d}-c{charge}'
    with (out/f'{name}.err').open('w')as log:
        p=subprocess.run(['/tmp/ahc074-overpatch',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt','300000',str(charge),'8'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=300)
    r=json.loads(p.stdout);r['seed']=seed;(out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,charge,r['difference'],r['novel'],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(job,[(s,c)for s in range(24,40)for c in (1.,1.5,2.)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for c in (1.,1.5,2.):
    v=[r['difference']for r in rows if r['charge']==c];print(c,statistics.mean(v),statistics.stdev(v)/math.sqrt(len(v)),flush=True)
