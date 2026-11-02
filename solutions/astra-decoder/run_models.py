"""Fixed-iteration models, at most eight child solvers; no tester processes."""
import concurrent.futures as cf
import json, os, pathlib, re, subprocess, time
D=pathlib.Path(__file__).resolve().parent
OUT=D/'data'; OUT.mkdir(exist_ok=True)
fixed=dict(MAP_ITERS='400000',GOPT_STEPS='100000',ANNEAL_ITERS='20000000',CLIMB_ITERS='60000',MODEL_ONLY='1',DUMP_DESIGN='1')
variants={'base':{},'free246':dict(COMPAT_FREE='26',COMPAT_GX='246'),'free230':dict(COMPAT_FREE='26',COMPAT_GX='230'),'free260':dict(COMPAT_FREE='26',COMPAT_GX='260'),'free300':dict(COMPAT_FREE='26',COMPAT_GX='300'),'free340':dict(COMPAT_FREE='26',COMPAT_GX='340'),'free380':dict(COMPAT_FREE='26',COMPAT_GX='380')}
# A completed seed writes its own atomic record; later analyses need no rerun.
def job(seed):
 rows=[]
 for name,ex in variants.items():
  path=OUT/f'{name}-{seed:04d}.json'
  if path.exists(): rows.append(json.loads(path.read_text()));continue
  env=os.environ|fixed|ex
  t=time.monotonic()
  with open(f'/home/sato/ahc074/tools/in/{seed:04d}.txt','rb') as inp:
   r=subprocess.run([str(D/'model')],stdin=inp,capture_output=True,env=env,timeout=180)
  if r.returncode:raise RuntimeError((seed,name,r.returncode,r.stderr[-2000:]))
  metrics={m[0]:float(m[1]) for m in re.findall(rb'(?m)^(\w+) = ([-+0-9.eE]+)$',r.stderr)}
  metrics={k.decode():v for k,v in metrics.items()}
  record={'seed':seed,'variant':name,'fixed':fixed,'extra':ex,'wall_sec':time.monotonic()-t,'metrics':metrics,'design':json.loads(r.stdout)}
  path.write_text(json.dumps(record,separators=(',',':'))+'\n');rows.append(record)
 return seed
if __name__=='__main__':
 with cf.ThreadPoolExecutor(max_workers=8) as pool:
  for seed in pool.map(job,range(24,88)): print('finished',seed,flush=True)
