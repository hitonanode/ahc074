from pathlib import Path
import json,subprocess,sys,os
root=Path(__file__).resolve().parents[2];runs=Path('/home/sato/ahc074/runs')
paths=['solutions/d30a-reset6','solutions/d30b-r6-headreset','solutions/d30b-r6-perfreset']
for p in paths[1:]:
 print('CLANG',p,flush=True)
 subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','clang++','-std=c++23','-O2','-march=native','-stdlib=libc++','-ftrivial-auto-var-init=zero','-DLOCAL_BENCH','-DCLOCK_SCALE=1.1',p+'/main.cpp','-o','/tmp/'+Path(p).name+'-clang'],cwd=root,check=True)
with (root/'solutions/implb-notes/r6-smoke.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/jflags-notes/run.py','--compare']+paths+['--seeds','0-20','--no-record','-c','B reset6 head/perforation reset smoke'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
last=sorted(runs.glob('*_d30b-r6-headreset'))[-1]
smoke=json.loads((last/'meta.json').read_text())['compare']['runs']
for name in smoke:
 c=json.loads((runs/name/'result.json').read_text())['cases'];assert len(c)==20 and all(x['score']>0 for x in c),name
print('SMOKE WA0',smoke,flush=True)
env=dict(os.environ);env['D30B_BUILD_CACHE']=smoke[0].split('_')[0]
with (root/'solutions/implb-notes/r6-500.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/implb-notes/cached_run.py','--compare']+paths+['--seeds','0-500','-c','B reset6: head reset6 and perforation reset6 individually; winners of stack1 V screen'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
last=sorted(runs.glob('*_d30b-r6-headreset'))[-1];group=json.loads((last/'meta.json').read_text())['compare']['runs']
(root/'solutions/implb-notes/r6-500-runs.json').write_text(json.dumps(group,indent=2)+'\n')
with (root/'solutions/implb-notes/r6-500-summary.txt').open('w') as f:
 subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,'solutions/implb-notes/summarize.py']+group+['--output','solutions/implb-notes/r6-500.json'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
print('RESET SCREEN COMPLETE',flush=True)
