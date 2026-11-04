from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'models';out.mkdir(exist_ok=True)
jobs=[(s,t,r,a)for s in range(24,28)for t,r,a in [(0.6,0,0),(1.,0,0),(0.6,0,1),(1.,0,1),(.6,1,0),(1.,1,0)]]
def job(item):
    seed,temp,start,accept=item;name=f'{seed:04d}-t{temp}-s{start}-a{accept}'
    with (out/f'{name}.err').open('w')as log:
        p=subprocess.run(['/tmp/ahc074-latent-code',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt','10000',str(temp),str(seed*1000003),str(start),str(accept)],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
    r=json.loads(p.stdout);r['seed']=seed;(out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,temp,start,accept,r['difference'],r['nonlinear'],r['last_nonlinear'],r['last_exact'],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(job,jobs))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
