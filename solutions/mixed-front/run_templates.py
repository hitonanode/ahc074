from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics
out=Path(__file__).parent/'templates';out.mkdir(exist_ok=True)
def task(seed):
 r=subprocess.run(['/tmp/ahc074-mixed-templates',f'tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt'],capture_output=True,text=True,check=True)
 x=json.loads(r.stdout);x['seed']=seed;(out/f'{seed:04}.json').write_text(json.dumps(x));return x
with ThreadPoolExecutor(max_workers=4)as pool:rows=list(pool.map(task,range(24,56)))
(out/'summary.json').write_text(json.dumps({'cases':len(rows),'rescued':statistics.mean(x['rescued'] for x in rows),'feasible':statistics.mean(x['feasible_templates'] for x in rows),'own_extra':statistics.mean(x['own_extra'] for x in rows)},indent=2))
print((out/'summary.json').read_text())
