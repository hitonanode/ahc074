"""最終通常2000件の集計、出力一致、ビルドと時間条件をまとめて照合する。"""
import subprocess
import sys
from pathlib import Path

here=Path(__file__).resolve().parent
base='20261106-043249_argon-des-perf-stratacut'
candidate='20261106-043249_argon-des-design-packed'
subprocess.run([sys.executable,str(here/'analyze_pair.py'),base,candidate,'packed2000','--end','2000'],check=True)
subprocess.run([sys.executable,str(here.parent/'argon-des-design-packed/final_audit.py'),base,candidate],check=True)
