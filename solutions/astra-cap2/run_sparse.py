from pathlib import Path
import concurrent.futures as cf,subprocess,os,json,time
r=Path(__file__).resolve().parent
def run(job):
 links,g,seed=job;name=f'sparse{links}g{g}-{seed:04d}';env=os.environ.copy();env.update(SPARSE_LINKS=str(links),G_PROBE=str(g),ONLY_SELECTOR='6')
 with open(f'/home/sato/ahc074/tools/in/{seed:04d}.txt','rb') as f:
  p=subprocess.run([str(r/'work/sparse_mapping')],stdin=f,capture_output=True,env=env,check=True)
 dump=r/'work'/f'{name}.out';dump.write_bytes(p.stdout)
 q=subprocess.run([str(r/'work/shared_cap_model'),str(dump)],capture_output=True,env=env,check=True)
 (r/'results'/f'{name}.csv').write_bytes(q.stdout)
 return name
jobs=[(l,g,s) for l in [1,2,3,4] for g in [34,36,38] for s in range(24,40)]
t=time.monotonic()
with cf.ThreadPoolExecutor(max_workers=8) as ex:
 for i,name in enumerate(ex.map(run,jobs)):
  if i%16==15:print(i+1,name,round(time.monotonic()-t,1),flush=True)
