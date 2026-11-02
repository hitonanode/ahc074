import concurrent.futures as cf, pathlib, subprocess
D=pathlib.Path(__file__).resolve().parent

def job(seed):
 dst=D/'data'/f'relax-{seed:04d}.jsonl'
 if dst.exists() and len(dst.read_text().splitlines())==9:return seed
 r=subprocess.run([str(D/'relax_probe'),str(D/'data'/f'{seed:04d}.snapshot')],capture_output=True,timeout=180)
 if r.returncode:raise RuntimeError((seed,r.returncode,r.stderr[-2000:]))
 dst.write_bytes(r.stdout);return seed
with cf.ThreadPoolExecutor(max_workers=8) as pool:
 for seed in pool.map(job,range(24,88)): print('finished',seed,flush=True)
