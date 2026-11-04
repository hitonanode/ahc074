from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;out=folder/'strong';out.mkdir(exist_ok=True)
def job(item):
 seed,start,beam=item;name=f'{seed:04d}-{start}-b{beam}';profile=folder/'partitions'/f'{seed:04d}-{start}-w5.txt'
 with (out/f'{name}.err').open('w') as log:
  p=subprocess.run(['/tmp/ahc074-long-fast',str(profile),'0','256','16384',str(beam),'-','600000007','0','0'],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
 r=json.loads(p.stdout);r.update(seed=seed,start=start,beam=beam);(out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,start,beam,r['validation'],r.get('fallback'),flush=True);return r
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(job,[(s,c,b) for s in range(24,28) for c in range(0,25,5) for b in (32,64)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for s in range(24,28):
 for b in (32,64):print('total',s,b,sum(r['validation'] for r in rows if r['seed']==s and r['beam']==b),flush=True)
