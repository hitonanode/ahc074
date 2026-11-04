from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
out=Path(__file__).parent/'validation';out.mkdir(exist_ok=True)
def task(job):
 s,p,w=job
 r=subprocess.run([f'/tmp/ahc074-reset-cost-{p}-prod',f'tools/in/{s:04}.txt',f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{s:04}.txt','16','20000000',str(w)],text=True,capture_output=True,check=True)
 (out/f'{s:04}-p{p}.json').write_text(r.stdout);(out/f'{s:04}-p{p}.err').write_text(r.stderr)
 a=json.loads(r.stdout)[0];assert not a['wrong'];a['seed']=s;a['priority']=p
 print(s,p,a['moves'],flush=True);return a
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(task,[(s,p,w) for s in range(56,120) for p,w in [(17,0),(20,2)]]))
reference={a['seed']:a['moves'] for a in rows if a['priority']==17}
x=[a['moves']-reference[a['seed']] for a in rows if a['priority']==20]
s={'cases':len(x),'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'win_tie_loss':[sum(a<0 for a in x),sum(a==0 for a in x),sum(a>0 for a in x)]}
(out/'summary.json').write_text(json.dumps(s,indent=2));print(s)
