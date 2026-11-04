from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json
folder=Path(__file__).resolve().parent
out=folder/'prices';out.mkdir(exist_ok=True)
jobs=[(24,'base','0024-base'),(25,'base','0025-base')]
jobs += [(int(p.name[:4]),str(p),p.stem)for p in sorted((folder/'joint').glob('*.json'))if p.name!='summary.json']
def task(job):
    seed,source,name=job;dest=out/f'{name}.json'
    if dest.exists():return json.loads(dest.read_text())
    data=subprocess.check_output(['python3',str(folder/'export_model.py'),str(seed),source],text=True)
    input=out/f'{name}.txt';input.write_text(data)
    r=subprocess.run(['/tmp/ahc074-triple-map-model',str(input),'10000000'],text=True,capture_output=True,check=True)
    dest.write_text(r.stdout);(out/f'{name}.err').write_text(r.stderr)
    rows=json.loads(r.stdout);print(name,rows,flush=True);return rows
with ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(task,jobs))
