from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent
out=folder/'wide';out.mkdir(exist_ok=True)
def job(item):
    seed,w=item;start=25-w;name=f'{seed:04d}-w{w}'
    saved=out/f'{name}.json'
    if saved.exists():return json.loads(saved.read_text())
    profile=out/f'{name}.txt'
    with profile.open('w') as f:subprocess.run(['python3',str(folder/'profile.py'),str(seed),str(start),str(w)],stdout=f,check=True)
    with (out/f'{name}.err').open('w') as log:
        p=subprocess.run(['/tmp/ahc074-long-module',str(profile),'700','8192','32768','8'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=7200)
    r=json.loads(p.stdout);r['seed']=seed;r['windows']=w
    (out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n')
    print(seed,w,r['difference'],r['best_train']-r['baseline_train'],r['elapsed'],flush=True)
    return r
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(job,[(s,w) for s in range(24,28) for w in (4,5)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
