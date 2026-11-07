from pathlib import Path
import subprocess,os,sys
P=Path(__file__).resolve().parent;root=P.parents[1]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
def run(log,args,extra={}):
 with (P/log).open('w') as f:
  subprocess.run([sys.executable,str(P/'run.py')]+args,cwd=root,env=dict(env,**extra),stdout=f,stderr=subprocess.STDOUT,check=True)
run('helper-request-train.log',['--compare']+['solutions/'+x for x in ['argon-des-perf-latew105','deval-vbranch-nofb','deval-flex125-plan3','deval-helper-wide','deval-helper-one']]+['--seeds','0-500','--save-design','--no-record','-c','Task6 last request-only training timing'])
for cc in ['g++','clang++']:
 for base,name in [('deval-equalwide-fast','deval-helper-wide'),('deval-helpeq-fast','deval-helper-one')]:
  run('last-identity-'+cc.replace('+','p')+'-'+name+'.log',['--compare','solutions/'+base,'solutions/'+name,'--seeds','0-200','--no-record','-c','Task6 exact composite '+cc],{'DEVAL_CXX':cc})
for name in ['deval-helper-wide','deval-helper-one','deval-helper-gap1']:
 for script in ['build_submission.py','build_native.py','source_audit.py']:
  with (root/'solutions'/name/(script+'.log')).open('w') as f:
   subprocess.run([sys.executable,str(P/script),name],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
