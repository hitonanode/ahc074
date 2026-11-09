"""Finish the diagnostic identity check and read-only paired analyses sequentially."""
import subprocess,sys
from pathlib import Path
notes=Path(__file__).resolve().parent;root=notes.parents[1]
subprocess.run([sys.executable,'-u',str(notes/'gbias_logcheck.py')],cwd=root,check=True)
for suite,n,arms in [('screen',500,[]),('screen',2000,['--arms','1']),('clang',2000,[])]:
 with (notes/f'gbias-{suite}-{n}-analysis.txt').open('w')as out:
  subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,str(notes/'gbias_analysis.py'),suite,'--end',str(n)]+arms,cwd=root,stdout=out,stderr=subprocess.STDOUT,check=True)
print('GBIAS FINAL ANALYSES READY',flush=True)
