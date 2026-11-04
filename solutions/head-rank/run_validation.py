from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
out=Path(__file__).parent/'validation';out.mkdir(exist_ok=True)
def task(s):
 p=subprocess.run(['/tmp/ahc074-head-rank',f'tools/in/{s:04}.txt',f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{s:04}.txt','16'],text=True,capture_output=True,check=True)
 (out/f'{s:04}.json').write_text(p.stdout);(out/f'{s:04}.err').write_text(p.stderr)
 x=json.loads(p.stdout);assert all(not a['wrong'] for a in x);print(s,[(a['weight'],a['difference']) for a in x],flush=True);return x
with ThreadPoolExecutor(max_workers=4) as pool:rows=sum(pool.map(task,range(56,88)),[])
summary=[]
for w in [.05,.1,.2,.4,.8]:
 data=[a for a in rows if a['weight']==w];x=[a['difference'] for a in data];summary.append({'weight':w,'cases':len(x),'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'win_tie_loss':[sum(a<0 for a in x),sum(a==0 for a in x),sum(a>0 for a in x)],'seconds':statistics.mean(a['seconds'] for a in data)})
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary)
