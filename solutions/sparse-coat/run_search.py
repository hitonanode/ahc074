from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json
out=Path(__file__).parent/'search';out.mkdir(exist_ok=True)
def task(job):
 s,d=job
 p=subprocess.run(['/tmp/ahc074-sparse-coat-search',f'tools/in/{s:04}.txt',f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{s:04}.txt',str(d),'100000','1'],text=True,capture_output=True,check=True)
 (out/f'{s:04}-d{d}.json').write_text(p.stdout);(out/f'{s:04}-d{d}.err').write_text(p.stderr)
 x=json.loads(p.stdout);g=x.pop('gates');(out/f'{s:04}-d{d}.txt').write_text(str(len(g))+'\n'+'\n'.join(' '.join(map(str,a)) for a in g)+'\n');print(s,x,flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(task,[(s,d) for s in range(24,28) for d in [2,3,4,5]]))
