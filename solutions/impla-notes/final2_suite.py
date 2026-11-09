"""Run named final2 checks through the standard pahcer runner; no solver runs here."""
import argparse,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('suite',choices=['identity','identity_final','bounds','pattern','normal','stretch','judge']);a=p.parse_args()
root=Path(__file__).resolve().parents[2];notes=root/'solutions/impla-notes'
g='-std=c++23 -O2 -DLOCAL_BENCH -DCLOCK_SCALE=1.1'
c='-O2 -std=gnu++23 -march=native -stdlib=libc++ -flto=auto -ftrivial-auto-var-init=zero -DLOCAL_BENCH -DCLOCK_SCALE=1.1'
gn=g+' -march=native'
base='solutions/final-time-pace-fix2';ref='solutions/d30a-reset6';cand='solutions/final2-reset6'
fixed=False;seeds='0-200'
if a.suite=='identity':
 arms=[(base,'g++',g),(ref,'g++',g),(cand,'g++',g),(base,'clang++',c),(ref,'clang++',c),(cand,'clang++',c),(ref,'g++',gn),(cand,'g++',gn)];fixed=True
elif a.suite=='identity_final':
 arms=[(cand,'g++',g),(cand,'clang++',c),(cand,'g++',gn)];fixed=True
elif a.suite=='bounds':
 arms=[(cand,'clang++',c+' -D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_DEBUG'),(cand,'g++',g+' -D_GLIBCXX_ASSERTIONS')]
elif a.suite=='pattern':
 arms=[(cand,'clang++',c.replace('-ftrivial-auto-var-init=zero','-ftrivial-auto-var-init=pattern')+' -DNOINIT_EMPTY')];fixed=True
elif a.suite=='normal':
 arms=[(base,'g++',g),(cand,'g++',g)];seeds='0-2000'
elif a.suite=='stretch':
 arms=[(cand,'g++',g+' -DPACE_SIM=1.35'),(cand,'g++',g+' -DPACE_SIM=2.0')]
elif a.suite=='judge':
 arms=[(cand,'clang++','-O2 -std=gnu++23 -march=native -stdlib=libc++ -ftrivial-auto-var-init=zero'),(cand,'g++','-O2 -std=gnu++23 -march=native -ftrivial-auto-var-init=zero')];seeds='0-50'
env=os.environ.copy()
for key in ['DESIGN_FIXED_ITERS','DESIGN_SECONDS','D30A_RESET']:env.pop(key,None)
if fixed:env['DESIGN_FIXED_ITERS']='1'
env['JFLAGS_ARMS']=json.dumps([[compiler,flags]for _,compiler,flags in arms])
command=[sys.executable,'-u',str(root/'solutions/final2-reset6/run.py')]
if len(arms)>1:command+=['--compare']
command += [s for s,_,_ in arms]+['--seeds',seeds,'-c','final2-reset6 '+a.suite+'; fixed='+str(int(fixed))]
(notes/('final2-'+a.suite+'-spec.json')).write_text(json.dumps({'suite':a.suite,'arms':arms,'fixed':fixed,'seeds':seeds,'command':command},ensure_ascii=False,indent=2)+'\n')
raise SystemExit(subprocess.run(command,env=env,cwd=root).returncode)
