from pathlib import Path
import time,json,re,subprocess
D=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
while True:
 try:
  ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',(D/'smoke.log').read_text(),re.M)
  if len(ids)==2 and all(json.loads((R/r/'meta.json').read_text()).get('status')=='ok'for r in ids):break
 except (OSError,ValueError):pass
 time.sleep(2)
subprocess.run(['flock','-x',str(R/'.lock'),'nice','-n','10','/home/sato/ahc074/.venv/bin/python','-B',str(D/'smoke_stats.py')],check=True)
