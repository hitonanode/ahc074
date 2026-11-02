import subprocess,sys,time
from pathlib import Path
p=Path(__file__).resolve().parent
while not (p/'results/shared12/summary.json').exists():time.sleep(2)
for label,width in [('forced4',4),('forced8',8)]:
 cmd=[sys.executable,str(p/'bench.py'),'--binary','forced','--label',label,'--seeds','24-40','--sim','4','--extra','GATE_TRIALS=128','--extra','GATE_WITNESSES=12','--extra',f'GATE_GROUP={width}']
 with (p/(label+'-run.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 print(label,'done',flush=True)
