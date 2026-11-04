from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
out=Path(__file__).parent/'models';out.mkdir(exist_ok=True)
def task(job):
 s,p=job
 r=subprocess.run([f'/tmp/ahc074-reset-cost-{p}-prod',f'tools/in/{s:04}.txt',f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{s:04}.txt','8','20000000'],text=True,capture_output=True,check=True)
 (out/f'{s:04}-p{p}.json').write_text(r.stdout);(out/f'{s:04}-p{p}.err').write_text(r.stderr)
 x=json.loads(r.stdout);assert all(not a['wrong'] for a in x)
 for a in x:a['seed']=s;a['priority']=p
 print(s,p,[(a['weight'],a['moves']) for a in x],flush=True);return x
with ThreadPoolExecutor(max_workers=4) as pool:rows=sum(pool.map(task,[(s,p) for s in range(24,56) for p in [17,20]]),[])
reference={a['seed']:a['moves'] for a in rows if a['priority']==17 and a['weight']==0}
summary=[]
for p in [17,20]:
 for w in [0.,.5,1.,2.]:
  data=[a for a in rows if a['priority']==p and a['weight']==w];x=[a['moves']-reference[a['seed']] for a in data];summary.append({'priority':p,'weight':w,'cases':len(x),'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'win_tie_loss':[sum(a<0 for a in x),sum(a==0 for a in x),sum(a>0 for a in x)],'design_seconds':statistics.mean(a['design_seconds'] for a in data)})
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary)
