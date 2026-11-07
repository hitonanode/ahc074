"""Finish the report after final_metrics.py succeeds; invoke this script under flock."""
from pathlib import Path
import subprocess,sys,os,json,hashlib
P=Path(__file__).resolve().parent;D=P.parent/sys.argv[1];root=P.parents[1]
x=json.loads((D/'final-metrics.json').read_text());f=json.loads((D/'FROZEN.json').read_text())
assert x['audit']['sha256']==f['sha256']==hashlib.sha256((D/'main.cpp').read_bytes()).hexdigest()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
for name in ['official_check.py','tail_audit.py','source_audit.py','reference_audit.py','write_report.py']:
 with (D/(name+'.log')).open('w') as out:
  subprocess.run([sys.executable,str(P/name),D.name],cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
assert (D/'REPORT.md').stat().st_size>1000
print(D/'REPORT.md')
