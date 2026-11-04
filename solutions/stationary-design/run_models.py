from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
out=Path(__file__).parent/'models';out.mkdir(exist_ok=True)
def task(seed):
 r=subprocess.run(['/tmp/ahc074-stationary-design',f'tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt','16','20000000'],text=True,capture_output=True,check=True)
 (out/f'{seed:04}.json').write_text(r.stdout);(out/f'{seed:04}.err').write_text(r.stderr)
 rows=json.loads(r.stdout);assert all(not a['wrong'] for a in rows)
 for a in rows:a['seed']=seed
 print(seed,[(a['weight'],a['difference'],a['price_seconds']) for a in rows],flush=True);return rows
with ThreadPoolExecutor(max_workers=4) as pool:rows=sum(pool.map(task,range(24,56)),[])
summary=[]
for weight in [.5,1]:
 data=[a for a in rows if a['weight']==weight];x=[a['difference'] for a in data]
 summary.append({'weight':weight,'cases':len(x),'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'win_tie_loss':[sum(a<0 for a in x),sum(a==0 for a in x),sum(a>0 for a in x)],'price_seconds':statistics.mean(a['price_seconds'] for a in data)})
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary)
