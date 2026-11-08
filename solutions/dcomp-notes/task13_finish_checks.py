"""Wait for both requested runs, then audit and render the report tables."""
from pathlib import Path
import subprocess,time
N=Path(__file__).resolve().parent
needed=['t13-final-clang.json','t13-final-runs.json','t13-store-check.json','t13-submission-builds.json']
while not all((N/f).exists()for f in needed):time.sleep(2)
for script in ['task13_audit.py','task13_report_results.py']:
 subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','/home/sato/ahc074/.venv/bin/python',str(N/script)],check=True)
print('Task13 final audits and report tables completed',flush=True)
