"""Measure the complete exact backend on 200 seeds, with both compilers."""
from pathlib import Path
import os, subprocess, sys, re
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
for compiler in ['g++','clang++']:
    tag='combined-gcc' if compiler=='g++' else 'combined-clang'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',DEVAL_CXX=compiler)
    with (P/(tag+'.log')).open('w') as f:
        subprocess.run([sys.executable,str(P/'run.py'),'--compare','solutions/deval-vbranch-nofb','solutions/deval-climbcache','--seeds','0-200','--no-record','-c','Task3 complete exact backend identity and time '+compiler],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    runs=re.findall(r'^\[pahcer_run\] run-id: (\S+)',(P/(tag+'.log')).read_text(),re.M)
    with (P/(tag+'-analysis.log')).open('w') as f:
        subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'compare_runs.py'),*runs,str(P/(tag+'.json'))],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    print(tag,runs,flush=True)
