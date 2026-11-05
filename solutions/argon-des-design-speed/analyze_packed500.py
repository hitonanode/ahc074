"""容量縮小を追加した版を、基準および距離表だけの版と比べる。"""
import subprocess
import sys
from pathlib import Path

here=Path(__file__).resolve().parent
base='20261106-043249_argon-des-perf-stratacut'
orbit='20261106-043249_argon-des-comparator-orbit'
packed='20261106-043249_argon-des-design-packed'
subprocess.run([sys.executable,str(here/'summarize.py'),base,orbit,packed,'--output','packed500.json'],check=True)
for name,label in [(orbit,'orbit-control500'),(packed,'packed500')]:
    subprocess.run([sys.executable,str(here/'identity.py'),base,name,'--end','500',
                    '--output',label+'-identity.json'],check=True)
