from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'search';out.mkdir(exist_ok=True)
def job(item):
    seed,enabled=item;name=f'{seed:04d}-e{enabled}'
    with (out/f'{name}.err').open('w')as log:
        p=subprocess.run(['/tmp/ahc074-overcoat-search',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt','100000',str(enabled)],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
    r=json.loads(p.stdout);r['seed']=seed;(out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,enabled,r['base'],r['best'],r['anchors'],r['novel'],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(job,[(s,e)for s in range(24,32)for e in (0,1)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
v=[next(r['best']for r in rows if r['seed']==s and r['enabled']==1)-next(r['best']for r in rows if r['seed']==s and r['enabled']==0)for s in range(24,32)];print('mean/se',statistics.mean(v),statistics.stdev(v)/math.sqrt(len(v)),flush=True)
