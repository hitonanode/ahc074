"""Verify that the diagnostic correction leaves fixed outputs unchanged."""
import json,os,re,subprocess,sys
from datetime import datetime
from pathlib import Path
notes=Path(__file__).resolve().parent;root=notes.parents[1]
assert datetime.now().strftime('%H:%M')<'14:35'
env=os.environ.copy()
for key in ['D30A_GBIAS','D30A_RESET','MAP_ITERS','ANNEAL_ITERS','GOPT_STEPS','AS_ELITE','AS_WORK']:env.pop(key,None)
env['JFLAGS_ARMS']=json.dumps([['g++','-std=c++23 -O2']]);env['D30A_ARMS_ENV']=json.dumps([{'D30A_GBIAS':'0.001'}])
log=notes/'gbias-logcheck.log'
with log.open('w')as f:
 subprocess.run([sys.executable,'-u',str(notes/'run.py'),'solutions/d30a-gbias','--seeds','0-20','-c','A gbias diagnostic-only correction; lambda 0.001 output identity'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
rid=re.findall(r'\[pahcer_run\] run-id: (\S+)',log.read_text())[0];base='20261109-132134_d30a-gbias-2';runs=Path('/home/sato/ahc074/runs')
cases=json.loads((runs/rid/'result.json').read_text())['cases'];bad=[s for s in range(20)if(runs/base/'out'/f'{s:04d}.txt').read_bytes()!=(runs/rid/'out'/f'{s:04d}.txt').read_bytes()]
data={'base':base,'candidate':rid,'n':len(cases),'wa':sum(c['score']<=0 for c in cases),'same':20-len(bad),'different':bad}
(notes/'gbias-logcheck.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');assert data['wa']==0 and data['same']==20;print(data)
