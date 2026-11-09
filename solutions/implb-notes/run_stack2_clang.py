from pathlib import Path
import json,subprocess,sys,os
root=Path(__file__).resolve().parents[2];runs=Path('/home/sato/ahc074/runs')
env=dict(os.environ);flags='-std=gnu++23 -O2 -march=native -stdlib=libc++ -flto=auto -ftrivial-auto-var-init=zero';env['JFLAGS_ARMS']=json.dumps([['clang++',flags],['clang++',flags]])
with (root/'solutions/implb-notes/stack2-clang2000.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/jflags-notes/run.py','--compare','solutions/d30a-reset6','solutions/d30b-stack2','--seeds','0-2000','-c','B stack2 confirmation, local Clang18 with judge flags including LTO and zero init'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
last=sorted(runs.glob('*_d30b-stack2'))[-1];group=json.loads((last/'meta.json').read_text())['compare']['runs']
(root/'solutions/implb-notes/stack2-clang-runs.json').write_text(json.dumps(group,indent=2)+'\n')
with (root/'solutions/implb-notes/stack2-clang2000-summary.txt').open('w') as f:
 subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,'solutions/implb-notes/summarize.py']+group+['--output','solutions/implb-notes/stack2-clang2000.json'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
