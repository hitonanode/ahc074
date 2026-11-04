from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;out=folder/'free';out.mkdir(exist_ok=True)
def job(seed):
    name=f'{seed:04d}';profile=out/f'{name}.txt'
    saved=out/f'{name}.json'
    if saved.exists():return json.loads(saved.read_text())
    with profile.open('w') as f:subprocess.run(['python3',str(folder/'profile.py'),str(seed),'22','3'],stdout=f,check=True)
    with (out/f'{name}.err').open('w') as log:
        p=subprocess.run(['/tmp/ahc074-long-free',str(profile),'1500','8192','32768','8','-','400000009','1'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=7200)
    r=json.loads(p.stdout);r['seed']=seed
    (out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,r['difference'],r['best_train']-r['baseline_train'],r['elapsed'],flush=True);return r
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(job,range(24,32)))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
