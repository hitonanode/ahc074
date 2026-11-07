from pathlib import Path
import os,subprocess,sys
P=Path(__file__).resolve().parent;root=P.parents[1]
for cc,n in [('g++',500),('clang++',250)]:
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',DEVAL_CXX=cc)
 with (P/('combined-'+cc.replace('+','p')+'.log')).open('w') as f:
  subprocess.run([sys.executable,str(P/'run.py'),'--compare','solutions/deval-equalwide6','solutions/deval-helper-wide','--seeds','0-'+str(n),'--no-record','-c','Task6 exact combined request optimizations '+cc],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
