"""Frozen-source final compare and held-out design replays, all through the runner."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];N=ROOT/'solutions/dcomp-notes';R=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser();p.add_argument('candidate');a=p.parse_args()
source=ROOT/'solutions'/a.candidate/'main.cpp'
digest=lambda:hashlib.sha256(source.read_bytes()).hexdigest()
freeze={'candidate':a.candidate,'sha256':digest(),'time':datetime.datetime.now().astimezone().isoformat(),'selected_on':'seeds 0-499 only; held-out data not inspected','reason':'best retained design candidate under the training time comparison; verify even if below 0.03% merging threshold'}
assert not (N/'FROZEN.json').exists();(N/'FROZEN.json').write_text(json.dumps(freeze,indent=2)+'\n')
manifest={'frozen':freeze}
def run(args,label,count):
 assert digest()==freeze['sha256']
 log=N/(label+'.log')
 with log.open('w') as f:subprocess.run([sys.executable,str(N/'run.py')]+args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
 ids=re.findall(r'\[pahcer_run\] run-id: (\S+)',log.read_text());assert ids
 for rid in ids:
  m=json.loads((R/rid/'meta.json').read_text());assert m['status']=='ok',(rid,m['status'])
  c=json.loads((R/rid/'result.json').read_text())['cases'];assert len(c)==count and all(x['score']>0 for x in c)
 manifest[label]=ids;(N/'final-runs.json').write_text(json.dumps(manifest,indent=2)+'\n');return ids
ids=run(['--compare','solutions/argon-des-perf-latew105','solutions/deval-helper-wide','solutions/legal-tie-fix','solutions/'+a.candidate,'--seeds','0-2000','--save-design','-c','Task8 frozen final: design-only budget efficiency, fixed iterations, unchanged legal-tie-fast requests'],'final-normal',2000)
base=run(['solutions/legal-tie-fast','--design-from','20261107-165305_deval-flex125-plan3','--orders','8','--seeds','500-1000','-c','Task8 held-out baseline, current request policy; source frozen'],'final-base-replay',500)
cand=run(['solutions/legal-tie-fast','--design-from',ids[-1],'--orders','8','--seeds','500-1000','-c','Task8 frozen held-out candidate design replay, current request policy'],'final-candidate-replay',500)
subprocess.run([sys.executable,str(N/'analyze.py'),base[0],cand[0],'--scores-only','--output',str(N/'final-heldout.json')],cwd=ROOT,check=True)
assert digest()==freeze['sha256']
