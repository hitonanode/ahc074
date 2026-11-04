from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json
p=Path(__file__).resolve().parent;out=p/'screen';out.mkdir(exist_ok=True)
def run(seed):
 r=subprocess.run(['/tmp/ahc074-front-star-screen',str(p.parent/'front-three'/f'{seed:04}.txt'),'10000','1024'],text=True,capture_output=True,check=True)
 (out/f'{seed:04}.json').write_text(r.stdout);(out/f'{seed:04}.err').write_text(r.stderr);d=json.loads(r.stdout);print(seed,d['final_baseline'],d['final'],flush=True);return d
with ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(run,range(24,40)))
