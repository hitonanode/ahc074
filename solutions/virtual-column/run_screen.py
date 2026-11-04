from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent
out=folder/'screens';out.mkdir(exist_ok=True)
def task(seed):
    r=subprocess.run(['/tmp/ahc074-virtual-screen',f'tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt'],text=True,capture_output=True,check=True)
    (out/f'{seed:04}.json').write_text(r.stdout)
    return json.loads(r.stdout)
with ThreadPoolExecutor(max_workers=2) as pool: rows=list(pool.map(task,range(24,56)))
result=[]
for i in range(8):
    x=[r[i]['difference'] for r in rows]
    result.append({'n':i+1,'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'wins':sum(v<0 for v in x)})
(out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
