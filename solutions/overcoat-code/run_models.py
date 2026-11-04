from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent; root=folder.parents[1]; out=folder/'models';out.mkdir(exist_ok=True)
def job(seed):
    with (out/f'{seed:04d}.err').open('w') as log:
        p=subprocess.run(['/tmp/ahc074-overcoat-probe',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=300)
    r=json.loads(p.stdout);r['seed']=seed
    (out/f'{seed:04d}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,r['anchors'],r['difference'],r['selected'],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(job,range(24,88)))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
v=[r['difference']for r in rows];print('mean/se',statistics.mean(v),statistics.stdev(v)/math.sqrt(len(v)),flush=True)
