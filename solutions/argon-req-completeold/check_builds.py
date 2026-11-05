from pathlib import Path
import subprocess,sys
p=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
for compiler in ['g++','clang++']:
 for bench in [False,True]:
  out=p/('build-'+compiler+('-bench' if bench else '-plain'))
  cmd=[compiler,'-std=c++23','-O2','-Wall','-Wextra']
  if bench:cmd+=['-DLOCAL_BENCH','-DCLOCK_SCALE=1.1']
  cmd += [str(p/'main.cpp'),'-o',str(out)]
  print(' '.join(cmd),flush=True)
  r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  print(r.stdout+r.stderr,end='',flush=True)
  assert r.returncode==0 and not r.stderr, (r.returncode,r.stderr)
  out.unlink()
print('All four builds passed with no warnings.')
