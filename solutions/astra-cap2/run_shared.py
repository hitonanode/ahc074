from pathlib import Path
import concurrent.futures as cf,subprocess
r=Path(__file__).resolve().parent
seeds=range(24,40)
def run(s):
 f=r/'work/grid-model-64'/f'c1g38-{s:04d}.out'
 p=subprocess.run([str(r/'work/shared_cap_model'),str(f)],capture_output=True,check=True)
 (r/'results'/f'shared-{s:04d}.csv').write_bytes(p.stdout)
 return s
with cf.ThreadPoolExecutor(max_workers=8) as ex:
 for s in ex.map(run,seeds): print(s,flush=True)
