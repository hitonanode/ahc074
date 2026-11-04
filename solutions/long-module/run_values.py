from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;out=folder/'values';out.mkdir(exist_ok=True)
def job(item):
 seed,beam,mode=item;profile=folder/'partitions'/f'{seed:04d}-20-w5.txt';name=f'{seed:04d}-b{beam}-v{mode}'
 saved=out/f'{name}.json'
 if saved.exists():return json.loads(saved.read_text())
 with (out/f'{name}.err').open('w') as log:
  p=subprocess.run(['/tmp/ahc074-long-value',str(profile),'0','256','32768',str(beam),'-','500000003','0',str(mode)],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=900)
 r=json.loads(p.stdout);r.update(seed=seed,beam=beam,mode=mode);(out/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n');print(seed,beam,mode,r['validation'],r.get('fallback'),flush=True);return r
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(job,[(s,b,m) for s in range(24,28) for b in (8,16) for m in (0,1,2)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
