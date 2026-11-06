"""Wait without holding the evaluation lock, then run both calibration analyses."""
from pathlib import Path
import os,sys,time,json,subprocess
HERE=Path(__file__).resolve().parent
if '--execute' in sys.argv:
    import refit_branch,refit_interventions
    refit_branch.main()
    refit_interventions.main()
else:
    wanted={f'trainbranch{i}' for i in range(4)}
    while True:
        rows=[json.loads(x) for x in (HERE/'experiments.jsonl').read_text().splitlines()]
        if wanted<={r['tag'] for r in rows}:break
        time.sleep(15)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,__file__,'--execute'],env=env,check=True)
