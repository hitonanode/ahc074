"""Summarize completed final artifacts without changing the frozen solver."""
from pathlib import Path
import subprocess,sys,os,time,json
S=Path(sys.argv[1]).resolve()
P=Path(__file__).resolve().parent
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
while True:
    try:
        evaluation=json.loads((S/'final-evaluation.json').read_text())
        builds=json.loads((S/'builds.json').read_text())
        if 'candidate_replay' in evaluation and len(builds)==2:
            assert all(b['exit_code']==0 for b in builds)
            break
    except (OSError,ValueError):
        pass
    time.sleep(10)
calls=[
    ['summarize_final.py',str(S)],
    ['audit_final.py',str(S),evaluation['normal'][-1],evaluation['candidate_replay']],
    ['report_experiments.py'],
    ['write_report.py',str(S)],
]
with (S/'final-analysis.log').open('w') as f:
    for script,*args in calls:
        subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/script),*args],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
assert json.loads((S/'audit.json').read_text())['checks_pass']
print(S/'REPORT.md',flush=True)
