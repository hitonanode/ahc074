import subprocess,sys,time
from pathlib import Path
p=Path(__file__).resolve().parent
while not (p/'results/forced8/summary.json').exists():time.sleep(2)
with (p/'six-control-run.log').open('w') as log:
 r=subprocess.run([sys.executable,str(p/'bench.py'),'--binary','six-control','--label','six-control'],stdout=log,stderr=subprocess.STDOUT)
raise SystemExit(r.returncode)
