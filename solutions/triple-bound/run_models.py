from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent
out=folder/'models';out.mkdir(exist_ok=True)
def task(seed):
    r=subprocess.run(['/tmp/ahc074-triple-bound',f'tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt','10000000',str(out/f'{seed:04}-groups.txt')],text=True,capture_output=True,check=True)
    (out/f'{seed:04}.json').write_text(r.stdout);(out/f'{seed:04}.err').write_text(r.stderr)
    rows=json.loads(r.stdout);print(seed,[(r['price'],r['difference'],r['triples'])for r in rows],flush=True);return rows
with ThreadPoolExecutor(max_workers=2) as pool: rows=list(pool.map(task,range(24,32)))
result=[]
for i in range(1,5):
    x=[r[i]['difference'] for r in rows]
    result.append({'price':rows[0][i]['price'],'cases':len(x),'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'mean_triples':statistics.mean(r[i]['triples']for r in rows)})
(out/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
