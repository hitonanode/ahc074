from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent;out=folder/'models';out.mkdir(exist_ok=True)
def job(seed):
    profile=out/f'{seed:04d}.txt';profile.write_text(subprocess.check_output(['python3',str(folder/'profile.py'),str(seed),'0','2'],text=True))
    with (out/f'{seed:04d}.err').open('w')as log:
        p=subprocess.run(['/tmp/ahc074-front-exact',str(profile)],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
    r=json.loads(p.stdout);r['seed']=seed;(out/f'{seed:04d}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,r['baseline'],r['best'],r['chain'],r['difference_chain'],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(job,range(24,40)))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for k in ('difference','difference_chain'):
    v=[r[k]for r in rows];print(k,statistics.mean(v),statistics.stdev(v)/math.sqrt(len(v)),flush=True)
