from pathlib import Path
import subprocess,sys,os
P=Path(__file__).resolve().parent
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
with (P/'chain-wide.log').open('w') as f:
    subprocess.run([sys.executable,str(P/'run.py'),'--compare','solutions/argon-des-perf-latew105','solutions/deval-vbranch-nofb','solutions/deval-chain-finish-o3','solutions/deval-chain-wide','--seeds','0-500','--save-design','--no-record','-c','Task3 last training: spend O3 saving on neutral width 3'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
with (P/'chain-wide-replays.log').open('w') as f:
    subprocess.run([sys.executable,str(P/'replay_compare.py'),str(P/'chain-wide.log'),'deval-chain-wide'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
