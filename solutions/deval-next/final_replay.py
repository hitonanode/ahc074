"""Choose by the frozen runtime rule, then evaluate the untouched test seeds."""
from pathlib import Path
import subprocess,sys,os,json,re
P=Path(__file__).resolve().parent;root=P.parents[1];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
with (P/'final-selection.log').open('w') as f:subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'select_final.py')],stdout=f,stderr=subprocess.STDOUT,check=True,env=env)
z=json.loads((P/'final-selection.json').read_text());c=z['choice'];print(json.dumps(c),flush=True)
with (P/'final-replay.log').open('w') as f:subprocess.run([sys.executable,str(P/'run.py'),'solutions/'+c['name'],'--design-from',c['normal_run'],'--orders','8','--seeds','500-1000','-c','Task4 凍結ソース 未使用500–999の8列検証'],cwd=root,stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',(P/'final-replay.log').read_text(),re.M);assert len(ids)==1
z['replay_run']=ids[0];(P/'final-runs.json').write_text(json.dumps(z,indent=2)+'\n');print(json.dumps(z),flush=True)
