from pathlib import Path
import json,subprocess,sys,os
root=Path(__file__).resolve().parents[2];runs=Path('/home/sato/ahc074/runs')
paths=['solutions/d30a-reset6']+['solutions/d30b-cover'+s for s in ['040','045','050']]
for p in paths[1:]:
 print('CLANG',p,flush=True)
 subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','clang++','-std=c++23','-O2','-march=native','-stdlib=libc++','-ftrivial-auto-var-init=zero','-DLOCAL_BENCH','-DCLOCK_SCALE=1.1',p+'/main.cpp','-o','/tmp/'+Path(p).name+'-clang'],cwd=root,check=True)
env=dict(os.environ);env['D30B_BUILD_CACHE']='20261109-123053'
with (root/'solutions/implb-notes/round3-cover-smoke.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/implb-notes/cached_run.py','--compare']+paths+['--seeds','0-20','--no-record','-c','B round3 cover .40/.45/.50 smoke, stay=.25'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
last=sorted(runs.glob('*_d30b-cover040'))[-1];smoke=json.loads((last/'meta.json').read_text())['compare']['runs']
for n in smoke:
 cs=json.loads((runs/n/'result.json').read_text())['cases'];assert len(cs)==20 and all(c['score']>0 for c in cs)
print('SMOKE WA0',smoke,flush=True)
env['D30B_BUILD_CACHE']=smoke[0].split('_')[0]
with (root/'solutions/implb-notes/round3-cover-500.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/implb-notes/cached_run.py','--compare']+paths+['--design-from','20261109-130035_d30a-reset6','--orders','4','--seeds','0-500','-c','B round3 cover-only .40/.45/.50, reset6 fixed designs, stay=.25'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
last=sorted(runs.glob('*_d30b-cover040'))[-1];group=json.loads((last/'meta.json').read_text())['compare']['runs'];(root/'solutions/implb-notes/round3-cover-runs.json').write_text(json.dumps(group,indent=2)+'\n')
with (root/'solutions/implb-notes/round3-cover-500-summary.txt').open('w') as f:
 subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,'solutions/implb-notes/summarize.py']+group+['--output','solutions/implb-notes/round3-cover-500.json'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
print('COVER SCREEN COMPLETE',flush=True)
