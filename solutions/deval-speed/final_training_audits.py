"""Audit the last training comparisons after their normal runs finish."""
from pathlib import Path
import time,subprocess,sys,os
P=Path(__file__).resolve().parent
while 'ダッシュボードを更新しました' not in (P/'chain-final-train.log').read_text():
    time.sleep(10)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
for a,b,out in [
 ('20261107-100214_deval-refinish8','20261107-102824_deval-refinish-fast','refinish-fast-identity'),
 ('20261107-104541_deval-chain-finish','20261107-104541_deval-chain-finish-o3','chain-final-o3'),
]:
    with (P/(out+'.log')).open('w') as f:
        subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'compare_runs.py'),a,b,str(P/(out+'.json'))],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
with (P/'last-training-analysis.log').open('w') as f:
    subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'analyze_all_complete.py')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
