import subprocess,sys
from pathlib import Path
p=Path(__file__).resolve().parent
for label,witness in [('shared15',15),('shared12',12)]:
 cmd=[sys.executable,str(p/'bench.py'),'--binary','shared','--label',label,'--sim','4','--extra','GATE_TRIALS=128','--extra',f'GATE_WITNESSES={witness}']
 with (p/(label+'-run.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 print(label,'done',flush=True)
