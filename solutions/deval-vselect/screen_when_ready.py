from pathlib import Path
import subprocess,time,os,re
HERE=Path(__file__).resolve().parent
PY='/home/sato/ahc074/.venv/bin/python'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
while True:
    log=HERE/'screenpool12.log'
    match=re.search(r'^screenpool12 design (\S+)',log.read_text() if log.exists() else '',re.M)
    if match:break
    time.sleep(10)
subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',PY,str(HERE/'fit_screen.py'),match[1]],env=env,check=True)
