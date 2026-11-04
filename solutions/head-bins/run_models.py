from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'models';out.mkdir(exist_ok=True)
def job(seed):
 with (out/f'{seed:04d}.err').open('w')as log:
  p=subprocess.run(['/tmp/ahc074-head-bins',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt','8'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
 r=json.loads(p.stdout)
 for v in r:v['seed']=seed
 (out/f'{seed:04d}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,[(v['mode'],v['iterations'],round(v['difference'],5))for v in r],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=sum(pool.map(job,range(24,56)),[])
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for mode in range(4):
 for iters in [65000,130000]:
  a=[r['difference']for r in rows if r['mode']==mode and r['iterations']==iters];print(mode,iters,statistics.mean(a),statistics.stdev(a)/math.sqrt(len(a)),flush=True)
