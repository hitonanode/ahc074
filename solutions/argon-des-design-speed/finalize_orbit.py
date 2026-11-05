"""最終通常2000件の集計、一致検査、採用条件の照合を順に実行する。"""
import subprocess
import sys
from pathlib import Path

here=Path(__file__).resolve().parent
base='20261106-041647_argon-des-perf-stratacut'
candidate='20261106-041647_argon-des-comparator-orbit'
subprocess.run([sys.executable,str(here/'analyze_pair.py'),base,candidate,'orbit2000','--end','2000'],check=True)
subprocess.run([sys.executable,str(here.parent/'argon-des-comparator-orbit/final_audit.py'),base,candidate],check=True)
