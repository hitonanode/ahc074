from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent
out=folder/'models';out.mkdir(exist_ok=True)
def task(seed):
    r=subprocess.run(['/tmp/ahc074-virtual-probe',f'tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt','16','2'],text=True,capture_output=True,check=True)
    (out/f'{seed:04}.json').write_text(r.stdout);(out/f'{seed:04}.err').write_text(r.stderr)
    rows=json.loads(r.stdout);print(seed,[r['difference'] for r in rows],flush=True);return rows
with ThreadPoolExecutor(max_workers=2) as pool: rows=list(pool.map(task,range(24,56)))
result=[]
for i in range(1,3):
    x=[r[i]['difference'] for r in rows]
    result.append({'n':i,'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'wins':sum(v<0 for v in x),'wrong':sum(r[i]['wrong'] for r in rows),'failures':sum(r[i]['failures'] for r in rows)})
(out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
