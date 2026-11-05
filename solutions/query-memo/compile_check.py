#!/usr/bin/env python3
"""Build checks only. Invoked with the shared evaluation lock held."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess, time
jobs=[(name,cxx,bench) for name in ['query-memo','cap-ablation','cap-ablation-g39'] for cxx in ['g++','clang++'] for bench in [False,True]]
def compile_one(job):
 name,cxx,bench=job
 dest=Path('/tmp')/('ahc074-'+name+'-'+cxx.replace('+','p')+('-local' if bench else '-judge'))
 cmd=[cxx,'-std=c++23','-O2','-Wall','-Wextra']
 if bench:cmd+=['-DLOCAL_BENCH','-DCLOCK_SCALE=1.1']
 cmd+=['solutions/'+name+'/main.cpp','-o',str(dest)]
 t=time.monotonic();r=subprocess.run(cmd,capture_output=True,text=True)
 return job,r.returncode,time.monotonic()-t,r.stdout+r.stderr
with ThreadPoolExecutor(max_workers=3) as pool:
 results=list(pool.map(compile_one,jobs))
for job,code,elapsed,output in results:
 print(job,'exit',code,'seconds',round(elapsed,2))
 if output:print(output)
raise SystemExit(any(code for job,code,elapsed,output in results))
