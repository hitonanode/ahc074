"""Freeze then run both requested recorded comparisons; no settings selected from them."""
from pathlib import Path
import hashlib,json,re,os,subprocess
N=Path(__file__).resolve().parent;R=N.parents[1]
names=['argon-des-perf-latew105','dcomp-combo-dual30','dcomp-time-same','dcomp-time-target']
hashes={n:hashlib.sha256((R/'solutions'/n/'main.cpp').read_bytes()).hexdigest()for n in names}
freeze=N/'t13-freeze.json';assert not freeze.exists();freeze.write_text(json.dumps(hashes,indent=2)+'\n')
env=os.environ.copy()
for k in ['DEVAL_CXX','DEVAL_NATIVE','DCOMP_COMPILERS','DESIGN_FIXED_ITERS','DESIGN_SECONDS']:env.pop(k,None)
allruns={}
for tag,count,clang in [('t13-final-gcc',2000,False),('t13-final-clang',500,True)]:
 for n,h in hashes.items():assert hashlib.sha256((R/'solutions'/n/'main.cpp').read_bytes()).hexdigest()==h
 e=env.copy()
 if clang:e.update(DEVAL_CXX='clang++',DEVAL_NATIVE='1')
 args=['--compare',*['solutions/'+n for n in names],'--seeds',f'0-{count}','--save-design','-c',f'Task13 frozen {tag}, same 1.05s and target 1.22s design deadlines; requests unchanged']
 with (N/(tag+'.log')).open('w')as f:
  subprocess.run(['nice','-n','10','python3',str(N/'task10_run.py'),*args],cwd=R,env=e,stdout=f,stderr=subprocess.STDOUT,check=True)
 runs=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',(N/(tag+'.log')).read_text(),re.M);assert len(runs)==4
 allruns[tag]=runs
 with (N/(tag+'-stats.log')).open('w')as f:
  subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','/home/sato/ahc074/.venv/bin/python',str(N/'task13_final_stats.py'),*runs,'--count',str(count),'--output',str(N/(tag+'.json'))],cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
 for n,h in hashes.items():assert hashlib.sha256((R/'solutions'/n/'main.cpp').read_bytes()).hexdigest()==h
 (N/'t13-final-runs.json').write_text(json.dumps(allruns,indent=2)+'\n')
print('Task13 requested comparisons complete',allruns,flush=True)
