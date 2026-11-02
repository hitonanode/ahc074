# Runs only one solver at a time alongside the principal eight-worker suite.
import os,subprocess
from pathlib import Path
p=Path(__file__).resolve().parent
for fee,extra in [(300,0),(300,1),(340,1)]:
 for seed in range(24,88):
  out=p/'data'/f'fees{fee}p{extra}-{seed:04d}.jsonl'
  if out.exists():continue
  env=os.environ|{'RELAX_GX':str(fee),'RELAX_EXTRA_PAPER':str(extra),'RELAX_SKIP_CAP':'1'}
  r=subprocess.run([str(p/'relax_fees'),str(p/'data'/f'{seed:04d}.snapshot')],env=env,capture_output=True,timeout=120)
  if r.returncode:raise RuntimeError((seed,fee,r.stderr[-1000:]))
  out.write_bytes(r.stdout)
 print(fee,extra,'done',flush=True)
