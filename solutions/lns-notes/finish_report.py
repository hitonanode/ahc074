"""Wait for already-queued frozen measurements, audit and render their report."""
from pathlib import Path
import json,os,subprocess,sys,time

h=Path(__file__).resolve().parent;root=h.parents[1]
while True:
    p=h/'heldout-runs.json'
    if p.exists() and len(json.loads(p.read_text()))==3:break
    time.sleep(10)
env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1'
with (h/'final-replay-audit.log').open('w') as f:
    subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',
                    sys.executable,str(h/'verify_replays.py')],cwd=root,env=env,
                   stdout=f,stderr=subprocess.STDOUT,check=True)
required=['heldout-b8-paired-metrics.json','diagnostic-star-fixed-metrics.json',
          'diagnostic-joint-fixed-metrics.json','final-star-labels-vs-control.json']
while not all((h/x).exists() for x in required):time.sleep(10)
for script in ['build_summary.py','render_diagnostics.py','render_report.py']:
    # These rendering steps read completed small JSON files only, not traces.
    with (h/(script[:-3]+'.log')).open('w') as f:
        subprocess.run(['nice','-n','10',sys.executable,str(h/script)],cwd=root,
                       env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
print('Frozen phase-1 report rendered; manual review remains.',flush=True)
