from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json
folder=Path(__file__).resolve().parent
out=folder/'joint';out.mkdir(exist_ok=True)
configs=[(8,34,5),(8,34,15),(9,36,10),(9,36,20),(10,36,10),(10,36,20),(11,38,20),(10,32,20)]
def task(job):
    seed,m,g,n=job;name=f'{seed:04}-m{m}g{g}t{n}'
    r=subprocess.run(['/tmp/ahc074-triple-dp-grid',str(folder.parent/'triple-bound/models'/f'{seed:04}-groups.txt'),str(m),str(g),'120','1812831','1',str(n)],text=True,capture_output=True,check=True)
    (out/f'{name}.json').write_text(r.stdout);(out/f'{name}.err').write_text(r.stderr)
    row=json.loads(r.stdout);row['seed']=seed;row['initial_triples']=n
    print(name,{k:v for k,v in row.items()if k not in ('edges','groups')},flush=True);return row
with ThreadPoolExecutor(max_workers=2) as pool: rows=list(pool.map(task,[(s,m,g,n)for s in (24,25)for m,g,n in configs]))
(out/'summary.json').write_text(json.dumps([{k:v for k,v in r.items()if k not in ('edges','groups')}for r in rows],indent=2))
