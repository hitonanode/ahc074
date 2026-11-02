from pathlib import Path
import subprocess
r=Path(__file__).resolve().parent
jobs=[]
for n in [1,2,4,8]:jobs.append((f'spare{n}',r/'work/spare',f'EXTRA_PAIRS={n}'))
for c,exe in [(1,'m5c1g34'),(2,'m5c2g33')]:
 for g in [30,32,34,36]:jobs.append((f'm5c{c}g{g}',r/'work'/exe,f'G_PROBE={g}'))
for name,b,e in jobs:
 with (r/'work'/f'{name}-model.log').open('w') as f:
  subprocess.run(['python3',str(r/'bench.py'),'--label',f'{name}-model','--model','--fixed','400000,100000,20000000,30000','--seeds','24:56','--threads','8','--bins',f'{name}={b}','--env',e],stdout=f,check=True)
 print(name,flush=True)
