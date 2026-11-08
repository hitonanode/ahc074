"""Run the frozen Task12 final checks, with no setting changes between stages."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys
R=Path(__file__).resolve().parents[2];N=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('candidate');a=p.parse_args()
assert re.fullmatch(r'dcomp-[a-z0-9-]+',a.candidate)
names=['argon-des-perf-latew105','dcomp-combo-alt1','dcomp-combo-dual25',a.candidate]
hashes={n:hashlib.sha256((R/'solutions'/n/'main.cpp').read_bytes()).hexdigest() for n in names}
freeze={'candidate':a.candidate,'hashes':hashes,'training_seeds':'0-499','fixed_designs':'20261108-155517_combo-m1-nine'}
fp=N/'t12-final-freeze.json';assert not fp.exists();fp.write_text(json.dumps(freeze,indent=2)+'\n')
base_env=os.environ.copy()
for k in ['DEVAL_CXX','DEVAL_NATIVE','DCOMP_COMPILERS']:base_env.pop(k,None)
def check():
 for n,h in hashes.items():assert hashlib.sha256((R/'solutions'/n/'main.cpp').read_bytes()).hexdigest()==h,n
def run(tag,args,env=None):
 check()
 log=N/(tag+'.log')
 with log.open('w') as f:
  subprocess.run(['nice','-n','10','python3',str(N/'task10_run.py'),*args],cwd=R,env=env or base_env,stdout=f,stderr=subprocess.STDOUT,check=True)
 runs=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',log.read_text(),re.M)
 for rid in runs:
  d=Path('/home/sato/ahc074/runs')/rid
  assert json.loads((d/'meta.json').read_text())['status']=='ok',rid
  assert all(c['score']>0 for c in json.loads((d/'result.json').read_text())['cases']),rid
 check();return runs
def analyze(tag,script,args):
 with (N/(tag+'-stats.log')).open('w') as f:
  subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','/home/sato/ahc074/.venv/bin/python',str(N/script),*args],cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
normal=run('t12-final-normal',['--compare',*[str(R/'solutions'/n) for n in names],'--save-design','-c','Task12 frozen final 2000, exact request speed reinvested on dual25'])
assert len(normal)==4
analyze('t12-final-normal','task12_final_stats.py',[*normal,'--output',str(N/'t12-final-normal.json')])
replay=run('t12-final-replay',['--compare','solutions/dcomp-combo-alt1','solutions/dcomp-combo-dual25','solutions/'+a.candidate,'--design-from','20261108-155517_combo-m1-nine','--orders','4','-c','Task12 frozen policy unseen-order final 2000 x 4'])
assert len(replay)==3
for label,ref in [('alt1',replay[0]),('dual25',replay[1])]:
 analyze('t12-final-replay-'+label,'task10_replay_stats.py',[ref,replay[2],'--output',str(N/('t12-final-replay-'+label+'.json'))])
env=base_env.copy();env.update(DEVAL_CXX='clang++',DEVAL_NATIVE='1')
clang=run('t12-final-clang',['--compare','solutions/dcomp-combo-alt1','solutions/dcomp-combo-dual25','solutions/'+a.candidate,'--seeds','0-500','-c','Task12 frozen final Clang native paired 500, same budgets'],env)
analyze('t12-final-clang','task10_analyze_log.py',['t12-final-clang',str(N/'t12-final-clang.log'),'--seeds','0-500'])
check()
(N/'t12-final-runs.json').write_text(json.dumps({'normal':normal,'replay':replay,'clang':clang,'freeze':freeze},indent=2)+'\n')
print('Task12 final checks complete:',a.candidate,normal,replay,clang,flush=True)
