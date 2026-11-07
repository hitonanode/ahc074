"""Run a normal compare followed by training replays. Every solver uses pahcer_run.py."""
from pathlib import Path
import os,subprocess,sys,re,json
P=Path(__file__).resolve().parent;R=P.parents[1];RUNS=Path('/home/sato/ahc074/runs')
tag=sys.argv[1];names=sys.argv[2:]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
def run(log,args,n,orders=1):
 with (P/log).open('w') as f:subprocess.run([sys.executable,str(P/'run.py')]+args,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 text=(P/log).read_text();assert 'ダッシュボードを更新しました' in text
 ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',text,re.M)
 for rid in ids:
  meta=json.loads((RUNS/rid/'meta.json').read_text());assert meta['status']=='ok'
  cases=json.loads((RUNS/rid/'result.json').read_text())['cases'];assert len(cases)==n
  assert all(len(c.get('order_scores',[c['score']]))==orders and min(c.get('order_scores',[c['score']]))>0 for c in cases)
 return ids
refs=['argon-des-perf-latew105','deval-seven-wide','deval-vbranch-nofb']
ids=run(tag+'.normal.log',['--compare']+['solutions/'+x for x in refs+names]+['--seeds','0-500','--save-design','--no-record','-c','Task4 training '+tag],500)
for name,design in zip(names,ids[len(refs):]):
 replay=run(name+'.replay.log',['solutions/'+name,'--design-from',design,'--orders','8','--seeds','0-500','-c','Task4 training replay '+name],500,8)[0]
 row={'tag':name,'design':design,'replay':replay,'seeds':[0,500],'normal_references':ids[:len(refs)]}
 with (P/'experiments.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 print(row,flush=True)
