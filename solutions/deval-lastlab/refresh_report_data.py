from pathlib import Path
import subprocess,sys,os
P=Path(__file__).resolve().parent;root=P.parents[1];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
def call(script,args,log,lock=True):
 cmd=(['flock','-x','/home/sato/ahc074/runs/.lock'] if lock else [])+[sys.executable,str(P/script)]+args
 with (P/log).open('w') as f:subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
call('summarize.py',[],'summary.log')
call('tables.py',[],'tables.log')
call('normal_frontier.py',['request-timing6.log','equalshift6.normal.log','equalfund6.normal.log','fast-frontier6.log','helper-final-train.log','helper-request-train.log'],'normal-frontier.log')
call('identity_extra.py',[],'identity-extra.log')
