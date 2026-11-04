from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent; root=folder.parents[1]; out=folder/'models';out.mkdir(exist_ok=True)
def job(seed):
    with (out/f'{seed:04d}.err').open('w') as log:
        p=subprocess.run(['/tmp/ahc074-head-generic',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt','8'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
    rows=json.loads(p.stdout)
    for r in rows:r['seed']=seed
    (out/f'{seed:04d}.json').write_text(json.dumps(rows,indent=2)+'\n');print(seed,[(r['strength'],r['difference'])for r in rows],flush=True);return rows
with ThreadPoolExecutor(max_workers=2)as pool:rows=sum(pool.map(job,range(24,40)),[])
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for k in (.01,.05,.1,.25,.5):
    a=[r['difference']for r in rows if r['strength']==k];print(k,statistics.mean(a),statistics.stdev(a)/math.sqrt(len(a)),flush=True)
