import subprocess,sys,time
from pathlib import Path
p=Path(__file__).resolve().parent
while not (p/'results/joint12/summary.json').exists():time.sleep(2)
for label,witness in [('joint-sa15',15),('joint-sa12',12)]:
 cmd=[sys.executable,str(p/'bench.py'),'--binary','joint-sa','--label',label,'--seeds','24-40','--sim','4','--extra','GATE_TRIALS=128','--extra',f'GATE_WITNESSES={witness}']
 with (p/(label+'-run.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 print(label,'done',flush=True)
