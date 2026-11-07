from pathlib import Path
import sys,subprocess,os,re,json
P=Path(__file__).resolve().parent;root=P.parents[1];R=Path('/home/sato/ahc074/runs');env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
def run(log,args,orders):
 with (P/log).open('w') as f:subprocess.run([sys.executable,str(P/'run.py')]+args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',(P/log).read_text(),re.M)
 for rid in ids:
  assert json.loads((R/rid/'meta.json').read_text())['status']=='ok'
  a=json.loads((R/rid/'result.json').read_text())['cases'];assert len(a)==500 and all(len(c.get('order_scores',[c['score']]))==orders and min(c.get('order_scores',[c['score']]))>0 for c in a)
 return ids
names=['argon-des-perf-latew105','deval-seven-wide','deval-vbranch-nofb','deval-ordered8-plan3']
n=run('plan3-combo.normal.log',['--compare']+['solutions/'+x for x in names]+['--seeds','0-500','--save-design','--no-record','-c','Task4 training eight candidates with equal-length plans'],1)
r=run('plan3-combo.replay.log',['--compare','solutions/deval-ordered8','solutions/deval-ordered8-plan3','--design-from','20261107-125002_deval-ordered8','--orders','8','--seeds','0-500','-c','Task4 training request combination on eight candidate designs'],8)
row={'tag':names[-1],'design':n[-1],'replay':r[-1],'seeds':[0,500],'normal_references':n[:3],'request_reference':r[0]}
with (P/'experiments.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
(P/'plan3-combo.json').write_text(json.dumps(row,indent=2)+'\n');print(row)
