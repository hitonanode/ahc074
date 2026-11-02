import subprocess,sys
from pathlib import Path
p=Path(__file__).resolve().parent
for binary,label,extra in [('model','base-sim',[]),('gates','gate128',['GATE_TRIALS=128']),('gates','compare128',['GATE_TRIALS=128','GATE_COMPARATORS=1'])]:
 cmd=[sys.executable,str(p/'bench.py'),'--binary',binary,'--label',label,'--sim','4']
 for x in extra:cmd+=['--extra',x]
 with (p/(label+'-run.log')).open('w') as log:
  r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 print(label,'done',flush=True)
