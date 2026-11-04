from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;out=folder/'partitions';out.mkdir(exist_ok=True)
def job(item):
    seed,start,w=item;name=f'{seed:04d}-{start}-w{w}';profile=out/f'{name}.txt'
    with profile.open('w') as f:subprocess.run(['python3',str(folder/'profile.py'),str(seed),str(start),str(w)],stdout=f,check=True)
    with (out/f'{name}.err').open('w') as log:
        p=subprocess.run(['/tmp/ahc074-long-module',str(profile),'0','256','16384','8'],capture_output=False,stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=300)
    r=json.loads(p.stdout);r.update(seed=seed,start=start,windows=w);(out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,start,r['baseline_validation'],flush=True);return r
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(job,[(s,c,5) for s in range(24,28) for c in range(0,25,5)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for s in range(24,28):print('total',s,sum(r['baseline_validation'] for r in rows if r['seed']==s),flush=True)
