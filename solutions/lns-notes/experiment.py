"""One fixed-budget phase-1 comparison and independent replays. No tests are tuned here."""
from pathlib import Path
import subprocess,sys,json,argparse,re,os,hashlib
here=Path(__file__).resolve().parent;root=here.parents[1];R=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('--lns',required=True);p.add_argument('--control',required=True);p.add_argument('--budget',type=int,choices=[2,4,8],required=True);p.add_argument('--seeds',default='0-500');p.add_argument('--baseline',required=True);a=p.parse_args()
assert a.lns.startswith('lns-') and a.control.startswith('lns-')
env=os.environ.copy();env['LNS_MULTIPLIER']=str(a.budget-1)
log=here/(a.tag+'-normal.log')
cmd=[sys.executable,str(here/'run.py'),'--compare','solutions/deval-helper-wide','solutions/'+a.lns,'solutions/'+a.control,'--seeds',a.seeds,'--save-design','--no-record','-c',f'Task7 phase1 {a.tag}: fixed source; budget {a.budget}x; LNS_MULTIPLIER={a.budget-1}; independent helper-wide replay follows']
with log.open('w') as f:subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
ids=re.findall(r'run-id: (\S+)',log.read_text());assert len(ids)==3,ids
for run in ids:assert json.loads((R/run/'meta.json').read_text())['status']=='ok'
record={'tag':a.tag,'budget':a.budget,'seeds':a.seeds,'normal':ids,'sources':{},'baseline':a.baseline}
for name in [a.lns,a.control]:record['sources'][name]=hashlib.sha256((root/'solutions'/name/'main.cpp').read_bytes()).hexdigest()
with (here/(a.tag+'-replays.log')).open('w') as f:
 subprocess.run([sys.executable,str(here/'replay_batch.py'),a.tag+'-replay',*ids[1:],'--seeds',a.seeds],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
rows=json.loads((here/(a.tag+'-replay.json')).read_text());record['replays']=[r['replay'] for r in rows]
(here/(a.tag+'-runs.json')).write_text(json.dumps(record,indent=2)+'\n')
for key,reference,targets in [('normal',ids[0],ids[1:]),('baseline',a.baseline,record['replays']),('paired',record['replays'][1],[record['replays'][0]])]:
 out=here/(a.tag+'-'+key+'-metrics.json')
 with (here/(a.tag+'-'+key+'-metrics.log')).open('w') as f:
  subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,str(here/'analyze.py'),reference,*targets,'--output',str(out)],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
print(json.dumps(record,indent=2),flush=True)
