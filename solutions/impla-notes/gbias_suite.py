"""Recorded fixed-iteration gbias checks through the standard pahcer runner."""
import argparse,json,os,subprocess,sys
from datetime import datetime
from pathlib import Path
root=Path(__file__).resolve().parents[2];notes=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('suite',choices=['smoke','screen','clang']);p.add_argument('--value',default='0.001');a=p.parse_args()
assert datetime.now().strftime('%H:%M') < '14:35', 'No new evaluation after 14:35 JST'
base='solutions/d30a-reset6';cand='solutions/d30a-gbias'
g=['g++','-std=c++23 -O2'];c=['clang++','-O2 -std=gnu++23 -march=native -stdlib=libc++ -flto=auto -ftrivial-auto-var-init=zero']
if a.suite=='smoke':arms=[(base,g,{}),(cand,g,{'D30A_GBIAS':'0'}),(cand,g,{'D30A_GBIAS':'0.001'}),(cand,g,{'D30A_GBIAS':'0.002'})];seeds='0-20'
elif a.suite=='screen':arms=[(base,g,{}),(cand,g,{'D30A_GBIAS':'0.001'}),(cand,g,{'D30A_GBIAS':'0.002'})];seeds='0-500'
else:arms=[(base,c,{}),(cand,c,{'D30A_GBIAS':a.value})];seeds='0-2000'
env=os.environ.copy()
for key in ['D30A_GBIAS','D30A_RESET','MAP_ITERS','ANNEAL_ITERS','GOPT_STEPS','AS_ELITE','AS_WORK']:env.pop(key,None)
env['JFLAGS_ARMS']=json.dumps([x[1]for x in arms]);env['D30A_ARMS_ENV']=json.dumps([x[2]for x in arms])
cmd=[sys.executable,'-u',str(notes/'run.py'),'--compare']+[x[0]for x in arms]+['--seeds',seeds,'-c','A gbias '+a.suite+' on reset6; lambda '+a.value]
if a.suite!='smoke':cmd+=['--save-design']
(notes/('gbias-'+a.suite+'-spec.json')).write_text(json.dumps({'arms':arms,'command':cmd},ensure_ascii=False,indent=2)+'\n')
raise SystemExit(subprocess.run(cmd,cwd=root,env=env).returncode)
