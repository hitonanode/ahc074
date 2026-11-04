from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'sweep';out.mkdir(exist_ok=True)
def job(seed):
 with (out/f'{seed:04d}.err').open('w')as log:
  p=subprocess.run(['/tmp/ahc074-design-head-sweep',str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt','8','65000','1'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
 r=json.loads(p.stdout)
 for v in r:v['seed']=seed
 (out/f'{seed:04d}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,[(v['mode'],v['weight'],round(v['difference'],5))for v in r],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=sum(pool.map(job,range(56,88)),[])
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for mode in [2]:
 for weight in [.6,1.,1.5,2.,3.]:
  a=[r['difference']for r in rows if r['mode']==mode and r['weight']==weight];print(mode,weight,statistics.mean(a),statistics.stdev(a)/math.sqrt(len(a)),flush=True)
