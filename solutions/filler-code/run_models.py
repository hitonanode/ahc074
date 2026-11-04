from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
p=Path(__file__).resolve().parent;out=p/'models';out.mkdir(exist_ok=True)
def run(seed):
 if seed==24:r=(p/'full-0024.json').read_text();err=(p/'full-0024.err').read_text()
 else:
  result=subprocess.run(['/tmp/ahc074-filler-code-full',f'/home/sato/ahc074/tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt','46','20000000','16'],text=True,capture_output=True,check=True);r=result.stdout;err=result.stderr
 (out/f'{seed:04}.json').write_text(r);(out/f'{seed:04}.err').write_text(err);d=json.loads(r);print(seed,{k:v for k,v in d.items()if k!='tests'},flush=True);return d
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,range(24,32)))
summary={}
for key in ('difference','helper_gain'):
 x=[r[key]for r in rows];summary[key]=dict(mean=statistics.mean(x),se=statistics.stdev(x)/math.sqrt(len(x)),wins=sum(v<0 for v in x),ties=sum(v==0 for v in x),losses=sum(v>0 for v in x))
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
