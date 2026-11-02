import subprocess,sys,time
from pathlib import Path
p=Path(__file__).resolve().parent
# The preceding suite owns the eight solver slots until its final summary exists.
while not (p/'results/compare128/summary.json').exists():time.sleep(2)
for label,extra in [('seven400',[]),('sparse4',['SPARSE_WINDOWS=4']),('sparse8',['SPARSE_WINDOWS=8']),('sparse12',['SPARSE_WINDOWS=12'])]:
 cmd=[sys.executable,str(p/'bench.py'),'--binary','seven','--label',label]
 for x in extra:cmd+=['--extra',x]
 with (p/(label+'-run.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 print(label,'done',flush=True)
