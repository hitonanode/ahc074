from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json
p=Path(__file__).resolve().parent;out=p/'models';out.mkdir(exist_ok=True)
configs=[(6,38,5,0),(6,38,15,0),(6,38,15,1),(7,38,10,0),(7,38,20,0),(7,38,20,1),(8,38,20,0),(8,38,20,1)]
def task(job):
 s,m,g,n,c=job;name=f'{s:04}-m{m}g{g}t{n}c{c}';dest=out/f'{name}.json'
 if dest.exists():return json.loads(dest.read_text())
 r=subprocess.run(['/tmp/ahc074-triple-free',str(p.parent/'triple-bound/models'/f'{s:04}-groups.txt'),str(m),str(g),'180','1812831',str(n),str(c)],text=True,capture_output=True,check=True)
 dest.write_text(r.stdout);(out/f'{name}.err').write_text(r.stderr)
 row=json.loads(r.stdout);row.update(seed=s,initial_triples=n,clipped=c);print(name,{k:v for k,v in row.items()if k not in ('patterns','groups')},flush=True);return row
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(task,[(s,*q)for s in(24,25)for q in configs]))
(out/'summary.json').write_text(json.dumps([{k:v for k,v in r.items()if k not in ('patterns','groups')}for r in rows],indent=2))
