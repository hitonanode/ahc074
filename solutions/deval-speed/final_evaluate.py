"""Freeze one candidate, run the required recorded compare, then its held-out replay.
Invoke only after selecting settings on seeds 0..499. This never selects a model.
"""
from pathlib import Path
import subprocess,sys,os,json,re,hashlib,datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[1];RUNS=Path('/home/sato/ahc074/runs')
PY='/home/sato/ahc074/.venv/bin/python'
solution=Path(sys.argv[1]);solution=solution if solution.is_absolute() else ROOT/solution
assert solution.parent==ROOT/'solutions' and solution.name.startswith('deval-')
source=(solution/'main.cpp').read_bytes();digest=hashlib.sha256(source).hexdigest()
freeze={'solution':solution.name,'sha256':digest,'source_bytes':len(source),'frozen_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'selection_seeds':[0,500],'test_seeds':[500,1000]}
(solution/'FROZEN.json').write_text(json.dumps(freeze,indent=2)+'\n')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
def call(tag,args,expected,orders=1):
 assert hashlib.sha256((solution/'main.cpp').read_bytes()).hexdigest()==digest
 log=solution/(tag+'.log')
 with log.open('w') as f:subprocess.run([PY,str(P/'run.py')]+args,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 text=log.read_text();assert 'ダッシュボードを更新しました' in text
 runs=re.findall(r'^\[pahcer_run\] run-id: (\S+)',text,re.M)
 for run in runs:
  meta=json.loads((RUNS/run/'meta.json').read_text());assert meta['status']=='ok',(run,meta['status'])
  cases=json.loads((RUNS/run/'result.json').read_text())['cases'];assert len(cases)==expected
  assert all(len(c.get('order_scores',[c['score']]))==orders and min(c.get('order_scores',[c['score']]))>0 for c in cases)
 print(tag,runs,flush=True);return runs
normal=call('final-normal',['--compare','solutions/argon-des-perf-latew105','solutions/deval-vbranch-nofb',str(solution),'--seeds','0-2000','--save-design','-c',f'Task3 final frozen {solution.name}: exact speedups reinvested in completed designs; no fallback'],2000)
out={'freeze':freeze,'normal':normal};(solution/'final-evaluation.json').write_text(json.dumps(out,indent=2)+'\n')
for key,name,design in [('baseline_replay','deval-vbranch-nofb',normal[1]),('candidate_replay',solution.name,normal[2])]:
 out[key]=call('final-'+key,['solutions/'+name,'--design-from',design,'--orders','8','--seeds','500-1000','-c',f'Task3 frozen held-out 500-999: {name}'],500,8)[0]
 (solution/'final-evaluation.json').write_text(json.dumps(out,indent=2)+'\n')
