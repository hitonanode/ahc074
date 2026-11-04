from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
out=Path(__file__).parent/'models';out.mkdir(exist_ok=True)
def task(job):
 s,c=job
 p=subprocess.run(['/tmp/ahc074-head-overlap',f'tools/in/{s:04}.txt',f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{s:04}.txt','8','5000',str(c)],text=True,capture_output=True,check=True)
 (out/f'{s:04}-s{c}.json').write_text(p.stdout);(out/f'{s:04}-s{c}.err').write_text(p.stderr)
 x=json.loads(p.stdout);assert all(not a['wrong'] for a in x);print(s,c,[(a['weight'],a['difference'],a['seconds']) for a in x],flush=True);return x
with ThreadPoolExecutor(max_workers=4) as pool:rows=sum(pool.map(task,[(s,c) for s in range(24,56) for c in [4,16]]),[])
summary=[]
for c in [4,16]:
 for w in [.6,1.,1.4]:
  data=[a for a in rows if a['copies']==c and a['weight']==w];x=[a['difference'] for a in data];summary.append({'copies':c,'weight':w,'cases':len(x),'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'win_tie_loss':[sum(a<0 for a in x),sum(a==0 for a in x),sum(a>0 for a in x)],'seconds':statistics.mean(a['seconds'] for a in data)})
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary)
