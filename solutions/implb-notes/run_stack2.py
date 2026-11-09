from pathlib import Path
import subprocess,json,sys,os
root=Path(__file__).resolve().parents[2];runs=Path('/home/sato/ahc074/runs');paths=['solutions/d30a-reset6','solutions/d30b-stack2']
assert (root/paths[1]/'main.cpp').read_bytes()==(root/'solutions/d30b-r6-perfreset/main.cpp').read_bytes()
subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','clang++','-std=c++23','-O2','-march=native','-stdlib=libc++','-ftrivial-auto-var-init=zero','-DLOCAL_BENCH','-DCLOCK_SCALE=1.1',paths[1]+'/main.cpp','-o','/tmp/d30b-stack2-clang'],cwd=root,check=True)
with (root/'solutions/implb-notes/stack2-smoke.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/jflags-notes/run.py','--compare']+paths+['--seeds','0-20','--no-record','-c','B stack2 reset6 plus perforation reset6 smoke'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
last=sorted(runs.glob('*_d30b-stack2'))[-1];smoke=json.loads((last/'meta.json').read_text())['compare']['runs']
for n in smoke:
 c=json.loads((runs/n/'result.json').read_text())['cases'];assert len(c)==20 and all(x['score']>0 for x in c)
print('SMOKE WA0',smoke,flush=True)
env=dict(os.environ);env['D30B_BUILD_CACHE']=smoke[0].split('_')[0]
with (root/'solutions/implb-notes/stack2-500.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/implb-notes/cached_run.py','--compare']+paths+['--seeds','0-500','-c','B stack2: reset6 plus perforation reset6 (head probability and hole cost)'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
last=sorted(runs.glob('*_d30b-stack2'))[-1];group=json.loads((last/'meta.json').read_text())['compare']['runs']
(root/'solutions/implb-notes/stack2-runs.json').write_text(json.dumps(group,indent=2)+'\n')
with (root/'solutions/implb-notes/stack2-500-summary.txt').open('w') as f:
 subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,'solutions/implb-notes/summarize.py']+group+['--output','solutions/implb-notes/stack2-500.json'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
print('STACK 500 COMPLETE',flush=True)
