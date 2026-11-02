import subprocess,sys,time
from pathlib import Path
p=Path(__file__).resolve().parent
while not (p/'results/sparse12/summary.json').exists():time.sleep(2)
experiments=[
 ('seven-tune','seven-h650',['HANDLE_WEIGHT=650'],0,'24-40'),
 ('seven-tune','seven-h800',['HANDLE_WEIGHT=800'],0,'24-40'),
 ('seven-tune','seven-h1000',['HANDLE_WEIGHT=1000'],0,'24-40'),
 ('seven-tune','seven-g40h650',['HANDLE_WEIGHT=650','SEVEN_G=40'],0,'24-40'),
 ('seven-tune','sparse6h650',['HANDLE_WEIGHT=650','SPARSE_WINDOWS=6'],0,'24-40'),
 ('joint-detail','joint15',['GATE_TRIALS=128'],4,'24-88'),
 ('joint-detail','joint12',['GATE_TRIALS=128','GATE_WITNESSES=12'],4,'24-88'),
]
for binary,label,extra,sim,seeds in experiments:
 cmd=[sys.executable,str(p/'bench.py'),'--binary',binary,'--label',label,'--seeds',seeds,'--sim',str(sim)]
 for x in extra:cmd+=['--extra',x]
 with (p/(label+'-run.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 print(label,'done',flush=True)
