from pathlib import Path
import subprocess,sys,os,json,re
P=Path(__file__).resolve().parent;root=P.parents[1];R=Path('/home/sato/ahc074/runs')
tag=sys.argv[1];names=sys.argv[2:]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
with (P/(tag+'.log')).open('w') as f:
 subprocess.run([sys.executable,str(P/'run.py'),'--compare','solutions/deval-flex125-plan3']+['solutions/'+x for x in names]+['--design-from','20261107-165305_deval-flex125-plan3','--orders','4','--seeds','0-500','-c','Task6 request '+tag],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',(P/(tag+'.log')).read_text(),re.M)
for r in ids:
 meta=json.loads((R/r/'meta.json').read_text());assert meta['status']=='ok'
 c=json.loads((R/r/'result.json').read_text())['cases'];assert len(c)==500 and all(len(x['order_scores'])==4 and min(x['order_scores'])>0 for x in c)
with (P/'requests.jsonl').open('a') as f:f.write(json.dumps({'tag':tag,'runs':ids})+'\n')
print(ids)
