from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json,statistics,math,sys
variant=int(sys.argv[1])if len(sys.argv)>1 else 0
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/['models','relaxed','flow','post'][variant];out.mkdir(exist_ok=True)
def job(seed):
    with (out/f'{seed:04d}.err').open('w')as log:
        p=subprocess.run([['/tmp/ahc074-global-assignment','/tmp/ahc074-global-relaxed','/tmp/ahc074-global-flow','/tmp/ahc074-global-post'][variant],str(root/'tools/in'/f'{seed:04d}.txt'),f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt','16','10',str(variant)],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
    r=json.loads(p.stdout)
    for v in r:v['seed']=seed
    (out/f'{seed:04d}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,r[1]['difference'],r[1]['model_after']-r[1]['model_before'],r[1]['unit_changes'],r[1]['handle_changes'],flush=True);return r
with ThreadPoolExecutor(max_workers=2)as pool:rows=sum(pool.map(job,range(24,56)),[])
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for k in ('difference',):
    v=[r[k]for r in rows if r['mode']==1];print(k,statistics.mean(v),statistics.stdev(v)/math.sqrt(len(v)),flush=True)
