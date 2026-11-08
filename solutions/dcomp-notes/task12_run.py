"""Task12 runner + completed-only analysis. All solves delegated to frozen wrapper."""
from pathlib import Path
import argparse,os,subprocess,sys
N=Path(__file__).resolve().parent;R=N.parents[1]
p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('--compiler',default='gcc');p.add_argument('--seeds',default='0-500');p.add_argument('--orders',type=int,default=1);p.add_argument('--replay',action='store_true');p.add_argument('solutions',nargs='+');a=p.parse_args()
env=os.environ.copy()
for k in ['DEVAL_CXX','DEVAL_NATIVE','DCOMP_COMPILERS']:env.pop(k,None)
if a.compiler=='clang':env.update(DEVAL_CXX='clang++',DEVAL_NATIVE='1')
if a.compiler=='gccnative':env['DEVAL_NATIVE']='1'
args=['--compare',*['solutions/'+s for s in a.solutions],'--seeds',a.seeds,'-c','Task12 '+a.tag]
if a.replay:args+=['--design-from','20261108-155517_combo-m1-nine','--orders',str(a.orders)]
else:assert a.orders==1
with (N/(a.tag+'.log')).open('w') as f:subprocess.run(['nice','-n','10',sys.executable,str(N/'task10_run.py'),*args],env=env,cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
with (N/(a.tag+'-stats.log')).open('w') as f:subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','/home/sato/ahc074/.venv/bin/python',str(N/'task10_analyze_log.py'),a.tag,str(N/(a.tag+'.log')),'--seeds',a.seeds,'--orders',str(a.orders)],cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
print('complete:',a.tag,flush=True)
