from pathlib import Path
import json,subprocess,sys,os
root=Path(__file__).resolve().parents[2];runs=Path('/home/sato/ahc074/runs')
paths=['solutions/d30a-reset6','solutions/d30b-stack2','solutions/d30b-perfcost6']
subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','clang++','-std=c++23','-O2','-march=native','-stdlib=libc++','-ftrivial-auto-var-init=zero','-DLOCAL_BENCH','-DCLOCK_SCALE=1.1',paths[2]+'/main.cpp','-o','/tmp/d30b-perfcost6-clang'],cwd=root,check=True)
env=dict(os.environ);env['D30B_BUILD_CACHE']='20261109-123053'
with (root/'solutions/implb-notes/perfcost-smoke.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/implb-notes/cached_run.py','--compare']+paths+['--seeds','0-20','--no-record','-c','B perf reset ablation: cost6 probability2 smoke'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
last=sorted(runs.glob('*_d30b-perfcost6'))[-1];smoke=json.loads((last/'meta.json').read_text())['compare']['runs']
for n in smoke:
 c=json.loads((runs/n/'result.json').read_text())['cases'];assert len(c)==20 and all(x['score']>0 for x in c)
print('SMOKE WA0',smoke,flush=True)
env['D30B_BUILD_CACHE']=smoke[0].split('_')[0]
with (root/'solutions/implb-notes/perfcost-500.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/implb-notes/cached_run.py','--compare']+paths+['--seeds','0-500','-c','B perf reset ablation: baseline reset6, accepted stack2, cost6 probability2'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
last=sorted(runs.glob('*_d30b-perfcost6'))[-1];group=json.loads((last/'meta.json').read_text())['compare']['runs'];(root/'solutions/implb-notes/perfcost-runs.json').write_text(json.dumps(group,indent=2)+'\n')
for tag,ids in [('perfcost-500',group),('perfcost-increment-500',group[1:])]:
 with (root/f'solutions/implb-notes/{tag}-summary.txt').open('w') as f:
  subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,'solutions/implb-notes/summarize.py']+ids+['--output',f'solutions/implb-notes/{tag}.json'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
print('PERFCOST SCREEN COMPLETE',flush=True)
