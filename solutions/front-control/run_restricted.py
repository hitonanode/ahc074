from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
out=Path(__file__).parent/'restricted';out.mkdir(exist_ok=True)
def task(job):
 seed,kind=job
 r=subprocess.run([f'/tmp/ahc074-front-control-{kind}',f'tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-162825_head-design/out/{seed:04}.txt','16'],text=True,capture_output=True,check=True)
 (out/f'{seed:04}-{kind}.json').write_text(r.stdout);(out/f'{seed:04}-{kind}.err').write_text(r.stderr)
 a=json.loads(r.stdout);assert not a['wrong'];a['seed']=seed;a['kind']=kind
 print(seed,kind,a['moves'],flush=True);return a
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(task,[(s,k) for s in range(24,56) for k in ['baseline','restricted']]))
reference={a['seed']:a['moves'] for a in rows if a['kind']=='baseline'}
x=[a['moves']-reference[a['seed']] for a in rows if a['kind']=='restricted']
s={'cases':len(x),'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'win_tie_loss':[sum(a<0 for a in x),sum(a==0 for a in x),sum(a>0 for a in x)]}
(out/'summary.json').write_text(json.dumps(s,indent=2));print(s)
