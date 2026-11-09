from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parents[2]
variants=json.loads((root/'solutions/implb-notes/cost-screen.json').read_text())
for x in variants:
 print('CLANG',x['path'],flush=True)
 subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','clang++','-std=c++23','-O2','-march=native','-stdlib=libc++','-ftrivial-auto-var-init=zero','-DLOCAL_BENCH','-DCLOCK_SCALE=1.1',x['path']+'/main.cpp','-o','/tmp/'+Path(x['path']).name+'-clang'],cwd=root,check=True)
args=[sys.executable,'solutions/jflags-notes/run.py','--compare','solutions/d30a-stack1']+[x['path'] for x in variants]
with (root/'solutions/implb-notes/cost-smoke.log').open('w') as f:
 subprocess.run(args+['--seeds','0-20','--no-record','-c','B design-cost audit: smoke 8 constants x2'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
print('SMOKE DONE: inspect before starting evaluation',flush=True)
