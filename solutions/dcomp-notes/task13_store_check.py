"""Check DesignStore on a final time-based design, using only pahcer executions."""
from pathlib import Path
import json,re,os,subprocess,time
N=Path(__file__).resolve().parent;R=N.parents[1];runs=Path('/home/sato/ahc074/runs')
while not (N/'t13-final-gcc.json').exists():time.sleep(2)
normal=json.loads((N/'t13-final-gcc.json').read_text())['runs'][-1]
env=os.environ.copy()
for k in ['DEVAL_CXX','DEVAL_NATIVE','DCOMP_COMPILERS','DESIGN_SECONDS','DESIGN_FIXED_ITERS']:env.pop(k,None)
log=N/'t13-store.log'
with log.open('w')as f:
 subprocess.run(['nice','-n','10','python3',str(N/'task10_run.py'),'--compare','solutions/dcomp-combo-dual30','solutions/dcomp-time-target','--design-from',normal,'--orders','1','--seeds','0-50','-c','Task13 DesignStore round trip and unchanged request policy on final saved designs'],env=env,cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',log.read_text(),re.M);assert len(ids)==2
# Read only 100 small outputs; no solver execution or CPU-heavy analysis here.
out={'design_run':normal,'replays':{}}
for rid in ids:
 d=runs/rid;m=json.loads((d/'meta.json').read_text());cs=json.loads((d/'result.json').read_text())['cases']
 assert m['status']=='ok' and not m['record'] and len(cs)==50 and all(c['score']>0 for c in cs)
 same=sum((d/'out'/f'{i:04d}.txt').read_bytes()==(runs/normal/'out'/f'{i:04d}.txt').read_bytes()for i in range(50))
 assert same==50
 metrics=json.loads((d/'metrics.json').read_text())['cases'];errors=sum(c['E']for c in metrics.values());assert errors==0
 out['replays'][rid]={'same':same,'total':50,'E':errors,'status':m['status'],'record':m['record']}
(N/'t13-store-check.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
