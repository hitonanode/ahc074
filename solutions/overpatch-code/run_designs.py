from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'designs';out.mkdir(exist_ok=True)
rows=json.loads((folder/'models/summary.json').read_text());jobs=[r for r in rows if r['seed']<32 and r['charge']in (1.,2.)]
def job(item):
    seed=item['seed'];name=f'{seed:04d}-c{item["charge"]}'
    with (out/f'{name}.err').open('w')as log:
        p=subprocess.run(['/tmp/ahc074-overpatch-design',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt',str(item['mask']),str(item['color']),str(item['handle']),str(item['handle_color']),str(item['charge']),'20000000'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=300)
    r=json.loads(p.stdout)
    for v in r:v.update(seed=seed,charge=item['charge'])
    (out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,item['charge'],r[-1]['difference'],r[-1]['special'],r[-1]['access_col'],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:result=sum(pool.map(job,jobs),[])
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
for c in (1.,2.):
    v=[r['difference']for r in result if r['charge']==c and r['kind']==1];print(c,statistics.mean(v),statistics.stdev(v)/math.sqrt(len(v)),flush=True)
