from pathlib import Path
import subprocess,sys,os,time
P=Path(__file__).resolve().parent
while not (P/'chain-seven.replay.log').exists() or 'ダッシュボードを更新しました' not in (P/'chain-seven.replay.log').read_text():
    time.sleep(10)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
with (P/'seven-wide.log').open('w') as f:
    subprocess.run([sys.executable,str(P/'run.py'),'--compare','solutions/deval-chain-seven','solutions/deval-seven-wide','--design-from','20261107-110423_deval-chain-seven','--orders','4','--seeds','0-500','-c','Task3 final fixed-design training: seven candidates plus neutral width 3'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
