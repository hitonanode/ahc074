"""Production-behavior smoke through the unchanged pahcer evaluation machinery."""
from pathlib import Path
import sys,importlib.util,os,json,re,subprocess,time
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
D=Path(__file__).resolve().parent;R=D.parents[1]
while not(D/'verification.json').exists():time.sleep(2)
while True:
 try:
  v=json.loads((D/'verification.json').read_text())
  if v.get('complete'):break
 except json.JSONDecodeError:pass
 time.sleep(2)
spec=importlib.util.spec_from_file_location('trim_pahcer',R/'scripts/pahcer_run.py');M=importlib.util.module_from_spec(spec);sys.modules[spec.name]=M;spec.loader.exec_module(M)
M.COMPILE_CMD=['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','g++','-std=gnu++23','-O2','-march=native','-ftrivial-auto-var-init=zero','-DCLOCK_SCALE=1.1','-ULOCAL_BENCH']
sys.argv=['scripts/pahcer_run.py','--compare',str(D/'time-original.cpp'),str(D/'time-production.cpp'),'--seeds','0-200','--no-record','-c','Task14 production trimming smoke, both arms without LOCAL_BENCH, CLOCK_SCALE=1.1, GCC native zero-init']
raise SystemExit(M.main())
