from pathlib import Path
import subprocess
import sys

p=Path(__file__).resolve().parent
base='20261106-054203_argon-req-ejectstats-v2'
candidates=['20261106-054203_argon-req-oldfull-v2','20261106-054203_argon-req-oldfull-consistent']
oracles=['20261106-054203_argon-req-oldfull-probe','20261106-054203_argon-req-oldfull-consistent-probe']
with (p/'calm-analysis.log').open('w') as out:
    subprocess.run([sys.executable,'solutions/argon-req-completeold/analyze.py',base,*candidates,'--end','200','--json',str(p/'calm-results.json')],stdout=out,stderr=subprocess.STDOUT,check=True)
with (p/'oracle-analysis.log').open('w') as out:
    subprocess.run([sys.executable,str(p/'analyze_oracles.py'),base,*oracles,'--json',str(p/'oracle-results.json')],stdout=out,stderr=subprocess.STDOUT,check=True)
print('Calm old-paper compare and output-identical oracle analysis complete.')
